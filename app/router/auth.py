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
from app.models.profile.profile import UserProfile
from app.models.profile.settings import UserSettings
import re


router = APIRouter(
    prefix='/api/auth',
    tags=["Authentication"]
)

async def create_username(db, email: str) -> str:
    base_username = email.split("@")[0].lower()
    base_username = re.sub(r"[^a-z0-9_]", "", base_username)

    if not base_username:
        base_username = "user"

    username = base_username
    counter = 1

    while True:
        result = await db.execute(
            select(User).where(User.username == username)
        )

        if result.scalar_one_or_none() is None:
            return username

        username = f"{base_username}{counter}"
        counter += 1


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: DBSession,
):
    existing_user = await user_service.get_user_with_email_or_username(
        db,
        user_data.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User already exists",
        )

    user = User(
        username=await create_username(db, user_data.email),
        email=user_data.email,
        hashed_password=password_manager.hash_password(
            user_data.password
        ),

        profile=UserProfile(
            display_name=user_data.email.split("@")[0],
        ),

        settings=UserSettings(),
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user

@router.post("/admin/sync-user-data")
async def sync_user_data(db: DBSession):
    # Get all users
    result = await db.execute(
        select(User.id, User.username)
    )

    users = result.all()

    user_ids = [user.id for user in users]

    if not user_ids:
        return {
            "message": "No users found",
            "users_checked": 0,
            "profiles_created": 0,
            "settings_created": 0,
        }

    # Existing profiles
    result = await db.execute(
        select(UserProfile.user_id).where(
            UserProfile.user_id.in_(user_ids)
        )
    )

    existing_profile_ids = set(result.scalars().all())

    # Existing settings
    result = await db.execute(
        select(UserSettings.user_id).where(
            UserSettings.user_id.in_(user_ids)
        )
    )

    existing_settings_ids = set(result.scalars().all())

    profiles_to_create = []
    settings_to_create = []

    for user_id, username in users:
        if user_id not in existing_profile_ids:
            profiles_to_create.append(
                UserProfile(
                    user_id=user_id,
                    display_name=username,
                )
            )

        if user_id not in existing_settings_ids:
            settings_to_create.append(
                UserSettings(
                    user_id=user_id,
                )
            )

    db.add_all(profiles_to_create)
    db.add_all(settings_to_create)

    await db.commit()

    return {
        "message": "User data sync completed",
        "users_checked": len(users),
        "profiles_created": len(profiles_to_create),
        "settings_created": len(settings_to_create),
    }


@router.post("/login")
async def login(request:Request,db:DBSession,form_data:Annotated[OAuth2PasswordRequestForm,Depends()]):
    user = await user_service.get_user_with_email_or_username(db,form_data.username)
    if not user:
        raise HTTPException(404,"User not found")
    if not password_manager.verify_password(form_data.password,user.hashed_password):
        raise HTTPException(401,"Invalid credentials")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device_id = request.headers.get("x-device-id")

    access_token = token_manager.create_access_token(str(user.id))
    refresh_token = await auth_service.store_refresh_token(db, user.id, ip_address, user_agent, device_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(db:DBSession,refresh_token:str):
    payload = token_manager.decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401,detail="Invalid token type")
    await auth_service.revoke_refresh_token(db,refresh_token)