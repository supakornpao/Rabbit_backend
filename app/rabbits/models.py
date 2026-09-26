from app.database import Base
import uuid

from sqlalchemy import UUID, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, func

class Rabbit(Base):
    __tablename__ = "rabbits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(100), index=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    breed = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)  # Store Unix timestamp
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)  # Store Unix timestamp