

from fastapi import APIRouter, Depends, HTTPException

from app.auth.router import get_current_user
from app.database import get_db
from app.auth import models as auth_models 
from app.rabbits import schemas, models
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
    db.delete(db_rabbit)
    db.commit()
    return {'message': 'Rabbit deleted successfully'}