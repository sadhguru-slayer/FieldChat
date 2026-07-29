from sqlalchemy import Text, ForeignKey, DateTime, Enum, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.models.base import Base,UUIDMixin
import enum
from uuid import UUID

class MessageType(enum.Enum):
    CHAT = "CHAT"
    SYSTEM = "SYSTEM"

class Message(UUIDMixin,Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True
    )

    sender_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    type: Mapped[MessageType] = mapped_column(
        Enum(MessageType),
        default=MessageType.CHAT
    )

    message: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted_global: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )

    sender = relationship(
        "User",
        back_populates="messages"
    )
    delete_states = relationship(
        "MessageDeleteState",
        cascade="all, delete-orphan"
    )

    receipts = relationship(
        "MessageReceipt",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_messages_conversation_time",
            "conversation_id",
            "timestamp"
        ),
    )

class MessageDeleteState(Base):
    __tablename__ = "message_delete_state"
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    deleted_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    message = relationship("Message")
    user = relationship("User")



class MessageReceipt(Base):
    __tablename__ = "message_receipts"

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    message = relationship(
        "Message",
        back_populates="receipts"
    )

    user = relationship("User")

    __table_args__ = (
        Index(
            "ix_receipts_user_read",
            "user_id",
            "read_at"
        ),
    )