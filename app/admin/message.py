from fastadmin import SqlAlchemyModelAdmin, register

from app.database import SessionLocal
from app.models.chat import (
    Message,
    MessageDeleteState,
    MessageReceipt,
)


@register(Message)
class MessageAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    list_display = [
        "id",
        "message",
        "conversation_id",
        "sender_id",
        "type",
        "timestamp",
        "edited_at",
        "is_deleted_global",
    ]

    search_fields = [
        "id",
        "message",
        "conversation_id",
        "sender_id",
    ]

    list_filter = [
        "type",
        "is_deleted_global",
        "timestamp",
        "edited_at",
    ]


@register(MessageDeleteState)
class MessageDeleteStateAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    list_display = [
        "message_id",
        "user_id",
        "deleted_at",
    ]

    search_fields = [
        "message_id",
        "user_id",
    ]

    list_filter = [
        "deleted_at",
    ]


@register(MessageReceipt)
class MessageReceiptAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    list_display = [
        "message_id",
        "user_id",
        "delivered_at",
        "read_at",
    ]

    search_fields = [
        "message_id",
        "user_id",
    ]

    list_filter = [
        "delivered_at",
        "read_at",
    ]