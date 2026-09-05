from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import  JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin

class OutboxEvent(Base,UUIDMixin):
    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_outbox_unprocessed",
            "processed_at",
            "created_at",
        ),
    )