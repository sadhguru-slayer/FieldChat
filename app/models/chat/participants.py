from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Enum,UniqueConstraint
from datetime import datetime,timezone
from app.models.base import Base,UUIDMixin
from .conversations import Conversation
import enum

from uuid import UUID
class ParticipantRole(enum.Enum):
    ADMIN="ADMIN"
    OWNER="OWNER"
    MEMBER="MEMBER"

class ConversationParticipant(UUIDMixin,Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participant",
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole),
        default=ParticipantRole.MEMBER,
        nullable=False
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default=lambda: datetime.now(timezone.utc),
    )

    last_read_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationship

    conversation = relationship(
        "Conversation",
        back_populates="participants"
    )

    user = relationship(
        "User",
        back_populates="conversations"
    )
    def __str__(self) -> str:
        return f"{self.user_id} — {self.conversation_id} ({self.role})"