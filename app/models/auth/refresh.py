from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import String, Boolean,DateTime,Enum, ForeignKey
import enum
from app.models.base import Base,UUIDMixin
from datetime import datetime

class RefreshToken(UUIDMixin,Base):
    __tablename__ = "refresh_tokens"
    user_id : Mapped[UUID] = mapped_column(
        ForeignKey("users.id",ondelete="CASCADE"),
        index=True
    )
    token_hash : Mapped[str] = mapped_column(String(64), unique=True)
    created_at:Mapped[datetime] = mapped_column(
      DateTime,
      default = datetime.utcnow  
    )
    updated_at:Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    device_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    device_name:Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    ip_address:Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    expires_at :Mapped[datetime] = mapped_column(DateTime)
    revoked:Mapped[bool] = mapped_column(Boolean,default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    user:Mapped["User"] = relationship(
        back_populates="refresh_tokens"
    )