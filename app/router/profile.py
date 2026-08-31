# app/routes/profile.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.services.storage_service import StorageService
from sqlalchemy import select

from app.models.profile.profile import UserProfile
from app.schema.profile.profile import (
    ProfileResponse,
    ProfileUpdate,
)
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service

profile_router = APIRouter(
    prefix="/api/users",
    tags=["Profile"],
)

@profile_router.get("/me/profile", response_model=ProfileResponse)
async def get_my_profile(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    current_user = await user_service.get_current_user(db, token)
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == current_user.id
        )
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        display_name = getattr(current_user, "name", None) or getattr(current_user, "username", None)
        profile = UserProfile(
            user_id=current_user.id,
            display_name=display_name,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile

@profile_router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    from app.models.auth.user import User
    from uuid import UUID
    
    target_user = await db.get(User, UUID(user_id))
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == target_user.id
        )
    )

    profile = result.scalar_one_or_none()
    
    display_name = getattr(target_user, "name", None) or getattr(target_user, "username", None)
    
    if profile:
        profile_data = {
            "display_name": profile.display_name or display_name,
            "bio": profile.bio,
            "custom_status": profile.custom_status,
            "avatar_url": profile.avatar_url,
            "date_of_birth": profile.date_of_birth,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    else:
        profile_data = {
            "display_name": display_name,
            "bio": None,
            "custom_status": None,
            "avatar_url": None,
            "date_of_birth": None,
            "created_at": getattr(target_user, "created_at", None),
            "updated_at": getattr(target_user, "updated_at", None),
        }
        
    return {
        "user_id": str(target_user.id),
        "username": target_user.username,
        "email": target_user.email,
        **profile_data
    }

@profile_router.patch("/me/profile", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    db: DBSession,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == token_user.id
        )
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        display_name = getattr(token_user, "name", None) or getattr(token_user, "username", None)
        profile = UserProfile(
            user_id=token_user.id,
            display_name=display_name,
        )
        db.add(profile)

    old_avatar = profile.avatar_url

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    if "avatar_url" in update_data and old_avatar and old_avatar != profile.avatar_url:
        storage_service = StorageService()
        background_tasks.add_task(storage_service.delete_media_by_url, old_avatar)

    return profile
