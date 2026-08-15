from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, Enum
from datetime import datetime,timezone
from app.models.base import Base,UUIDMixin
import enum

class ConversationType(enum.Enum):
    PERSONAL="PERSONAL"
    GROUP="GROUP"

class Conversation(UUIDMixin,Base):
    __tablename__ = "conversations"

    type:Mapped[ConversationType] = mapped_column(
        Enum(ConversationType)
    )

    name:Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    created_at :Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda:datetime.now(timezone.utc),
        index=True
    )
    is_deleted :Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Relationships
    participants = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"{self.type.value} - {self.id}"
