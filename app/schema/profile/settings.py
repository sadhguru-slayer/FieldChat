# app/schemas/profile/settings.py


from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.profile.settings import (
    Theme,
    Language,
    Visibility,
)


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Appearance
    theme: Theme
    language: Language

    # Notifications
    notifications_enabled: bool
    message_notifications: bool
    mention_notifications: bool
    sound_enabled: bool

    # Privacy
    profile_visibility: Visibility
    avatar_visibility: Visibility
    last_seen_visibility: Visibility
    read_receipts_enabled: bool

    # Chat
    enter_to_send: bool
    media_auto_download: bool

    # Metadata
    created_at: datetime
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    # Appearance
    theme: Theme | None = None
    language: Language | None = None

    # Notifications
    notifications_enabled: bool | None = None
    message_notifications: bool | None = None
    mention_notifications: bool | None = None
    sound_enabled: bool | None = None

    # Privacy
    profile_visibility: Visibility | None = None
    avatar_visibility: Visibility | None = None
    last_seen_visibility: Visibility | None = None
    read_receipts_enabled: bool | None = None

    # Chat
    enter_to_send: bool | None = None
    media_auto_download: bool | None = None
