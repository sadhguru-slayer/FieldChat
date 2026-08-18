# app/schemas/profile/profile.py

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None
    bio: str | None
    date_of_birth: date | None
    custom_status: str | None
    avatar_url: str | None

    created_at: datetime
    updated_at: datetime


from datetime import date
from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(
        default=None,
        max_length=100,
    )

    bio: str | None = Field(
        default=None,
        max_length=1000,
    )

    date_of_birth: date | None = None

    custom_status: str | None = Field(
        default=None,
        max_length=100,
    )

    avatar_url: str | None = Field(
        default=None,
        max_length=500,
    )
