import uuid
import enum
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base

class LimbEnum(str, enum.Enum):
    front_left = "front_left"
    front_right = "front_right"
    back_left = "back_left"
    back_right = "back_right"

class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    rabbit_id = Column(UUID(as_uuid=True), ForeignKey("rabbits.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url = Column(String, nullable=False)
    limb = Column(Enum(LimbEnum), nullable=False, default=LimbEnum.front_left)
    status = Column(String(20), nullable=False, default="analyzed")  # pending, processing, analyzed, failed
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    rabbit = relationship("app.rabbits.models.Rabbit", backref="photos")
    detection_result = relationship("DetectionResult", back_populates="photo", uselist=False, cascade="all, delete-orphan")

class DetectionResult(Base):
    __tablename__ = "detection_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), index=True, nullable=False)
    classification = Column(Integer, nullable=False)  # 0: Healthy, 1: Grade I, 2: Grade II, etc.
    confidence = Column(Float, nullable=True, default=0.95)
    analyzed_at = Column(DateTime, server_default=func.now(), nullable=False)

    photo = relationship("Photo", back_populates="detection_result")
