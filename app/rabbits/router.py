from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.auth.router import get_current_user
from app.database import get_db
from app.auth import models as auth_models 
from app.rabbits import schemas, models
from app.storage import upload_file_to_minio, delete_file_from_minio
from sqlalchemy.orm import Session
from uuid import UUID
router = APIRouter(prefix="/rabbits", tags=["rabbits"])

@router.post("/", response_model=schemas.Rabbit)
def create_rabbit(
    rabbit: schemas.RabbitCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)  # JWT user
):
    db_rabbit = models.Rabbit(
        **rabbit.model_dump(),
        owner_id=current_user.id  # Automatically set from token!
    )
    db.add(db_rabbit)
    db.commit()
    db.refresh(db_rabbit)
    return db_rabbit

@router.get("/", response_model=list[schemas.Rabbit])
def get_rabbits(
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    return db.query(models.Rabbit).filter(models.Rabbit.owner_id == current_user.id).all()

@router.get("/{rabbit_id}",response_model=schemas.Rabbit)
def get_rabbit_details(
    rabbit_id: UUID,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    db_rabbit = db.query(models.Rabbit).filter(models.Rabbit.id == rabbit_id, models.Rabbit.owner_id == current_user.id).first()
    if not db_rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found")
    return db_rabbit

@router.put("/{rabbit_id}", response_model=schemas.Rabbit)
def update_rabbit(
    rabbit_id: UUID,
    rabbit: schemas.RabbitUpdate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    db_rabbit = db.query(models.Rabbit).filter(models.Rabbit.id == rabbit_id, models.Rabbit.owner_id == current_user.id).first()
    if not db_rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found")
    for key, value in rabbit.model_dump().items():
        setattr(db_rabbit, key, value)
    db.commit()
    db.refresh(db_rabbit)
    return db_rabbit

@router.delete("/{rabbit_id}")
def delete_rabbit(
    rabbit_id: UUID,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    db_rabbit = db.query(models.Rabbit).filter(models.Rabbit.id == rabbit_id, models.Rabbit.owner_id == current_user.id).first()
    if not db_rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found")
    if db_rabbit.image_url:
        # e.g., "/media/users/{user_id}/avatars/..." -> strip "/media/"
        object_name = db_rabbit.image_url.replace("/media/", "", 1)
        delete_file_from_minio(object_name)
    for photo in getattr(db_rabbit, "photos", []):
        if photo.image_url:
            scan_object_name = photo.image_url.replace("/media/", "", 1)
            delete_file_from_minio(scan_object_name)
    db.delete(db_rabbit)
    db.commit()
    return {'message': 'Rabbit deleted successfully'}

@router.post("/{rabbit_id}/photo", response_model=schemas.Rabbit)
async def upload_rabbit_photo(
    rabbit_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    db_rabbit = db.query(models.Rabbit).filter(
        models.Rabbit.id == rabbit_id,
        models.Rabbit.owner_id == current_user.id
    ).first()
    if not db_rabbit:
        raise HTTPException(status_code=404, detail="Rabbit not found")

    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"

    object_name = f"users/{current_user.id}/avatars/{rabbit_id}.{ext}"
    old_object_name = db_rabbit.image_url.replace("/media/", "", 1) if db_rabbit.image_url else None

    media_url = upload_file_to_minio(file_bytes, object_name, content_type=content_type)

    if old_object_name and old_object_name != object_name:
        delete_file_from_minio(old_object_name)

    db_rabbit.image_url = media_url
    db.commit()
    db.refresh(db_rabbit)
    return db_rabbit
