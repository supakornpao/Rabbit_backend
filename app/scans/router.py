import uuid
import random
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.router import get_current_user
from app.auth import models as auth_models
from app.rabbits import models as rabbit_models
from app.scans import models as scan_models, schemas as scan_schemas
from app.storage import upload_file_to_minio

router = APIRouter(prefix="/scans", tags=["scans"])

GRADE_DETAILS = {
    0: {
        "grade_title": "Healthy: Normal Paw",
        "risk_level": "None",
        "explanation": "No signs of pododermatitis. The paw pads have good hair coverage with no inflammation or redness.",
        "surveillance_period": "Routine monthly check"
    },
    1: {
        "grade_title": "Grade I: Early Stage",
        "risk_level": "Low",
        "explanation": "Hair loss on the sole, thickened and red skin, but no open wound. Action: Change flooring to soft fleece/mats and trim nails.",
        "surveillance_period": "1–2 weeks"
    },
    2: {
        "grade_title": "Grade II: Mild Ulceration",
        "risk_level": "Moderate",
        "explanation": "Increased inflammation, swelling, redness, and shallow abrasions. Action: Clean the wound, apply prescribed ointment, and improve flooring.",
        "surveillance_period": "5–7 days"
    },
    3: {
        "grade_title": "Grade III: Deep Ulceration & Infection",
        "risk_level": "High",
        "explanation": "Deep open wounds, bleeding, severe inflammation, and possible pus. The rabbit may experience pain and reluctance to move. Action: Visit an Exotic Vet.",
        "surveillance_period": "Immediate vet visit"
    },
    4: {
        "grade_title": "Grade IV: Tendon Involvement",
        "risk_level": "Severe",
        "explanation": "Infection spreads into deep tissues and flexor tendons with severe swelling and chronic pain. Action: Urgent veterinary treatment required.",
        "surveillance_period": "Urgent veterinary care"
    },
    5: {
        "grade_title": "Grade V: Osteomyelitis",
        "risk_level": "Critical",
        "explanation": "Severe bone infection (Osteomyelitis) and loss of foot function. Action: Emergency medical treatment.",
        "surveillance_period": "Emergency veterinary hospital"
    }
}

@router.post("/", response_model=scan_schemas.ScanResponse)
async def process_paw_scan(
    rabbit_id: UUID = Form(...),
    limb: str = Form("front_left"),
    mock_grade: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    # 1. Verify rabbit ownership
    rabbit = db.query(rabbit_models.Rabbit).filter(
        rabbit_models.Rabbit.id == rabbit_id,
        rabbit_models.Rabbit.owner_id == current_user.id
    ).first()
    if not rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found or does not belong to you")

    # 2. Upload file to MinIO
    photo_id = uuid.uuid4()
    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    object_name = f"scans/{rabbit_id}/{photo_id}.{ext}"
    media_url = upload_file_to_minio(file_bytes, object_name, content_type=content_type)

    # 3. Create Photo record
    # Validate limb enum or fallback to front_left
    limb_value = limb if limb in [e.value for e in scan_models.LimbEnum] else scan_models.LimbEnum.front_left.value
    db_photo = scan_models.Photo(
        id=photo_id,
        rabbit_id=rabbit_id,
        image_url=media_url,
        limb=limb_value,
        status="analyzed",
    )
    db.add(db_photo)
    db.commit()

    # 4. Generate mock detection result (or use requested mock_grade if provided)
    chosen_classification = mock_grade if mock_grade is not None and 0 <= mock_grade <= 5 else random.choice([1, 2, 3])
    confidence = round(random.uniform(0.88, 0.98), 2)

    db_result = scan_models.DetectionResult(
        id=uuid.uuid4(),
        photo_id=db_photo.id,
        classification=chosen_classification,
        confidence=confidence
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_photo)
    db.refresh(db_result)

    # 5. Build rich response
    info = GRADE_DETAILS.get(chosen_classification, GRADE_DETAILS[1])
    return scan_schemas.ScanResponse(
        photo_id=db_photo.id,
        rabbit_id=rabbit_id,
        image_url=db_photo.image_url,
        limb=db_photo.limb.value if hasattr(db_photo.limb, 'value') else str(db_photo.limb),
        status=db_photo.status,
        classification=db_result.classification,
        confidence=db_result.confidence,
        grade_title=info["grade_title"],
        risk_level=info["risk_level"],
        explanation=info["explanation"],
        surveillance_period=info["surveillance_period"],
        analyzed_at=db_result.analyzed_at
    )

@router.get("/{photo_id}", response_model=scan_schemas.ScanResponse)
def get_scan_result(
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    photo = db.query(scan_models.Photo).filter(scan_models.Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Scan photo not found")

    rabbit = db.query(rabbit_models.Rabbit).filter(
        rabbit_models.Rabbit.id == photo.rabbit_id,
        rabbit_models.Rabbit.owner_id == current_user.id
    ).first()
    if not rabbit:
        raise HTTPException(status_code=403, detail="Not authorized to view this scan")

    result = photo.detection_result
    classification = result.classification if result else 0
    info = GRADE_DETAILS.get(classification, GRADE_DETAILS[0])

    return scan_schemas.ScanResponse(
        photo_id=photo.id,
        rabbit_id=photo.rabbit_id,
        image_url=photo.image_url,
        limb=photo.limb.value if hasattr(photo.limb, 'value') else str(photo.limb),
        status=photo.status,
        classification=classification,
        confidence=result.confidence if result else None,
        grade_title=info["grade_title"],
        risk_level=info["risk_level"],
        explanation=info["explanation"],
        surveillance_period=info["surveillance_period"],
        analyzed_at=result.analyzed_at if result else photo.uploaded_at
    )

@router.get("/rabbit/{rabbit_id}", response_model=list[scan_schemas.ScanResponse])
def get_rabbit_scans(
    rabbit_id: UUID,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    rabbit = db.query(rabbit_models.Rabbit).filter(
        rabbit_models.Rabbit.id == rabbit_id,
        rabbit_models.Rabbit.owner_id == current_user.id
    ).first()
    if not rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found or does not belong to you")

    photos = db.query(scan_models.Photo).filter(
        scan_models.Photo.rabbit_id == rabbit_id
    ).order_by(scan_models.Photo.uploaded_at.desc()).all()

    results = []
    for photo in photos:
        dr = photo.detection_result
        classification = dr.classification if dr else 0
        info = GRADE_DETAILS.get(classification, GRADE_DETAILS[0])
        results.append(scan_schemas.ScanResponse(
            photo_id=photo.id,
            rabbit_id=photo.rabbit_id,
            image_url=photo.image_url,
            limb=photo.limb.value if hasattr(photo.limb, 'value') else str(photo.limb),
            status=photo.status,
            classification=classification,
            confidence=dr.confidence if dr else None,
            grade_title=info["grade_title"],
            risk_level=info["risk_level"],
            explanation=info["explanation"],
            surveillance_period=info["surveillance_period"],
            analyzed_at=dr.analyzed_at if dr else photo.uploaded_at
        ))
    return results

