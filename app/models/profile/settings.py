import enum
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Theme(enum.Enum):
    SYSTEM = "SYSTEM"
    LIGHT = "LIGHT"
    DARK = "DARK"


class Language(enum.Enum):
    EN = "EN"
    HI = "HI"


class Visibility(enum.Enum):
    EVERYONE = "EVERYONE"
    CONTACTS = "CONTACTS"
    NOBODY = "NOBODY"


class UserSettings(UUIDMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # --------------------------------------------------
    # Appearance
    # --------------------------------------------------

    theme: Mapped[Theme] = mapped_column(
        Enum(Theme),
        default=Theme.SYSTEM,
        nullable=False,
    )

    language: Mapped[Language] = mapped_column(
        Enum(Language),
        default=Language.EN,
        nullable=False,
    )

    # --------------------------------------------------
    # Notifications
    # --------------------------------------------------

    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    message_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    mention_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    sound_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # --------------------------------------------------
    # Privacy
    # --------------------------------------------------

    profile_visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility),
        default=Visibility.EVERYONE,
        nullable=False,
    )

    avatar_visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility),
        default=Visibility.EVERYONE,
        nullable=False,
    )

    last_seen_visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility),
        default=Visibility.CONTACTS,
        nullable=False,
    )

    read_receipts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # --------------------------------------------------
    # Chat
    # --------------------------------------------------

    enter_to_send: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    media_auto_download: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --------------------------------------------------
    # Relationship
    # --------------------------------------------------

    user: Mapped["User"] = relationship(
        back_populates="settings",
    )
