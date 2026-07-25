from fastapi import APIRouter,HTTPException,Request,Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy import select

from app.dependencies import DBSession
from app.schema.auth.user import UserRegister,UserResponse

from app.models.auth.user import UserRole,User

from app.core.security.password import password_manager
from app.core.security.auth import token_manager

from app.services.user import user_service
from app.services.auth import auth_service

import re


router = APIRouter(
    prefix='/api/auth',
    tags=["Authentication"]
)

async def create_userame(db,email:str):
    base_username = email.split("@")[0].lower()
    base_username = re.sub(r"[^a-z0-9_]", "", base_username)
    if not base_username:
        base_username="user"

    username = base_username
    counter = 1
    while True:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            break

        username = f"{base_username}{counter}"
        counter += 1


    return username

@router.post('/register',response_model=UserResponse)
async def register(user_data:UserRegister,db:DBSession):
    existing_user = await user_service.get_user_with_email_or_username(db,user_data.email)
    if existing_user:
        raise HTTPException(400,"User already exists")
    user = User(
        username=await create_userame(db,user_data.email),
        email=user_data.email,
        hashed_password=password_manager.hash_password(user_data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user

@router.post("/token")
async def token(request:Request,db:DBSession,form_data:Annotated[OAuth2PasswordRequestForm,Depends()]):
    user = await user_service.get_user_with_email_or_username(db,form_data.username)
    if not user:
        raise HTTPException(404,"User not found")
    if not password_manager.verify_password(form_data.password,user.hashed_password):
        raise HTTPException(401,"Invalid credentials")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token = token_manager.create_access_token(str(user.id))
    refresh_token = await auth_service.store_refresh_token(db,user.id,ip_address,user_agent)
    return {
        "access_token":access_token,
        "refresh_token":refresh_token,
        "token_type":"bearer"
    }

