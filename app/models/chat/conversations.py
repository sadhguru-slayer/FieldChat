from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, Enum
from datetime import datetime,timezone
from app.models.base import Base,UUIDMixin
import enum

class ConversationType(enum.Enum):
    PERSONAL:"PERSONAL"
    GROUP:"GROUP"

class Conversation(UUIDMixin,Base):
    __tablename__ = "conversations"

    type:Mapped[ConversationType] = mapped_column(
        Enum(ConversationType)
    )

    name:Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )