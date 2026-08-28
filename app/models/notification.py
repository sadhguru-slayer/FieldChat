import enum
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class NotificationType(str, enum.Enum):
    MESSAGE = "MESSAGE"
    MENTION = "MENTION"
    REACTION = "REACTION"
    SYSTEM = "SYSTEM"
    ALERT = "ALERT"


class Notification(UUIDMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType),
        default=NotificationType.SYSTEM,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        backref="notifications",
    )
