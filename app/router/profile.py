# app/routes/profile.py

from fastapi import APIRouter, HTTPException, Depends
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
    prefix="/api/users/me/profile",
    tags=["Profile"],
)

@profile_router.get("",response_model=ProfileResponse)
async def get_my_profile(
    db: DBSession,
    token:str = Depends(oauth2_scheme),
):
    current_user = await user_service.get_current_user(db,token)
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == current_user.id
        )
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )

    return profile

@profile_router.patch("", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    db: DBSession,
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
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return profile
