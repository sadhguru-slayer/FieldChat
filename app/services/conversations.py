from sqlalchemy import select, and_
from app.dependencies import DBSession
from app.models.chat.participants import ConversationParticipant
from uuid import UUID

class ConversationService:
    @staticmethod
    async def is_user_participant(db:DBSession, conversation_id:UUID, user_id:UUID):
        result = await db.execute(
            select(ConversationParticipant.id).where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

conversation_service = ConversationService()