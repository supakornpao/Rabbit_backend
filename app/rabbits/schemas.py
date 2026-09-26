from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime

class RabbitCreate(BaseModel):
    name: str
    date_of_birth: date
    breed: str

class RabbitUpdate(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    breed: str | None = None

class Rabbit(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    date_of_birth: date
    breed: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True