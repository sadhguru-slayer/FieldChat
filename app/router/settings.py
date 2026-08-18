# app/routes/settings.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.models.profile.settings import UserSettings
from app.schema.profile.settings import (
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service


settings_router = APIRouter(
    prefix="/api/users/me/settings",
    tags=["Settings"],
)

@settings_router.get(
    "",
    response_model=UserSettingsResponse,
)
async def get_my_settings(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(
        db,
        token,
    )

    result = await db.execute(
        select(UserSettings).where(
            UserSettings.user_id == token_user.id
        )
    )

    settings = result.scalar_one_or_none()

    if settings is None:
        raise HTTPException(
            status_code=404,
            detail="Settings not found",
        )

    return settings


@settings_router.patch(
    "",
    response_model=UserSettingsResponse,
)
async def update_my_settings(
    data: UserSettingsUpdate,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(
        db,
        token,
    )

    result = await db.execute(
        select(UserSettings).where(
            UserSettings.user_id == token_user.id
        )
    )

    settings = result.scalar_one_or_none()

    if settings is None:
        raise HTTPException(
            status_code=404,
            detail="Settings not found",
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    return settings
