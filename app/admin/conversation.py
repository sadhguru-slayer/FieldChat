from fastadmin import SqlAlchemyModelAdmin, register

from app.database import SessionLocal
from app.models.chat.conversations import Conversation
from app.models.chat.participants import ConversationParticipant


@register(Conversation)
class ConversationAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    list_display = [
        "id",
        "type",
        "name",
        "created_at",
        "is_deleted",
    ]

    search_fields = [
        "name",
    ]

    list_filter = [
        "type",
        "is_deleted",
    ]


@register(ConversationParticipant)
class ConversationParticipantAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    list_display = [
        "id",
        "conversation_id",
        "user_id",
        "role",
        "joined_at",
        "last_read_message_id",
    ]

    search_fields = [
        "conversation_id",
        "user_id",
    ]

    list_filter = [
        "role",
    ]