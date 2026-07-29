from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, Enum
from datetime import datetime,timezone
import enum
from app.models.base import Base,UUIDMixin

class UserRole(enum.Enum):
    ADMIN="ADMIN"
    USER="USER"
    MODERATOR="MODERATOR"

class User(UUIDMixin,Base):
    __tablename__ = "users"

    username:Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )

    email:Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index = True
    )
    hashed_password:Mapped[str] = mapped_column(String(255))

    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    role:Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER
    )
    is_active:Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Relationships
    refresh_tokens:Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    conversations = relationship(
        "ConversationParticipant",
        back_populates="user",
        cascade="all, delete-orphan"
    )
