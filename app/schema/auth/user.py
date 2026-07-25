from pydantic import BaseModel,EmailStr
from uuid import UUID
from datetime import datetime

from app.models.auth.user import UserRole

class UserRegister(BaseModel):
    email:EmailStr
    password:str

class UserResponse(BaseModel):
    id: UUID
    username:str
    email:EmailStr
    role:UserRole
    is_active:bool
    created_at:datetime

    model_config = {
        "from_attributes":True
    }