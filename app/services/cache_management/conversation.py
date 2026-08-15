from app.redis_client import r
from sqlalchemy import select
from app.models.chat.conversations import Conversation
from app.models.chat.participants import ConversationParticipant
from app.redis.keys import RedisKeys

class ConversationCachee:

    @classmethod
    async def add_member(cls, conversation_id:str, user_id:str):
        # Adding user_id to conversation : conv_id : (user_id1,user_id2)
        await r.sadd(
            RedisKeys.conversation_members(conversation_id),
            user_id
        )
        # Adding conv_id to user : user_id : (conv_id1,conv_id2)
        await r.sadd(
            RedisKeys.user_conversations(user_id),
            conversation_id
        )

    @classmethod
    async def remove_member(cls, conversation_id: str, user_id:str):
        await r.srem(
            RedisKeys.conversation_members(conversation_id),
            user_id
        )

        # Remove reverse mapping
        await r.srem(
            RedisKeys.user_conversations(user_id),
            conversation_id
        )

    @classmethod
    async def get_member(cls, member_id:str,conversation_id:str):
        members = await r.smembers(
            RedisKeys.conversation_members(conversation_id)
        )
        return [m for m in members]

