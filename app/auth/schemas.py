from pydantic import BaseModel, EmailStr
from uuid import UUID

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class User(UserBase):
    id: UUID
    username: str | None = None
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
