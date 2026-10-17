from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class DetectionResultBase(BaseModel):
    classification: int
    confidence: float | None = None

class DetectionResult(DetectionResultBase):
    id: UUID
    photo_id: UUID
    analyzed_at: datetime

    class Config:
        from_attributes = True

class PhotoBase(BaseModel):
    rabbit_id: UUID
    limb: str
    status: str

class Photo(PhotoBase):
    id: UUID
    image_url: str
    uploaded_at: datetime
    detection_result: DetectionResult | None = None

    class Config:
        from_attributes = True

class ScanResponse(BaseModel):
    photo_id: UUID
    rabbit_id: UUID
    image_url: str
    limb: str
    status: str
    classification: int
    confidence: float | None = None
    grade_title: str
    risk_level: str
    explanation: str
    surveillance_period: str
    analyzed_at: datetime
