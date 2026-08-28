from app.redis_client import r
from sqlalchemy import select
from app.models.chat.conversations import Conversation
from app.models.chat.participants import ConversationParticipant
from app.redis.keys import RedisKeys
from uuid import UUID

class ConversationCache:
    # Member Management
    @classmethod
    async def add_members(
        cls,
        conversation_id: str,
        user_ids: list[str],
    ):
        conv_key = RedisKeys.conversation_members(conversation_id)

        async with r.pipeline() as pipe:
            pipe.sadd(conv_key, *user_ids)

            for user_id in user_ids:
                pipe.sadd(
                    RedisKeys.user_conversations(user_id),
                    conversation_id,
                )

            await pipe.execute()
    
    @classmethod
    async def get_user_conversations(cls, user_id:str):
        conversations = await r.smembers(
            RedisKeys.user_conversations(user_id)
        )
        return conversations

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

    @classmethod
    async def is_member(cls,conversation_id:str, member_id:str ):
        return await r.sismember(
            RedisKeys.conversation_members(conversation_id),
            member_id
        )
    # ==================================================================================
    @classmethod
    async def sync_conversation(cls, conversation_id:str,db):
        scalars = await db.scalars(
            select(ConversationParticipant.user_id)
            .where(ConversationParticipant.conversation_id == UUID(conversation_id))
        )
        user_ids = [str(user_id) for user_id in scalars.all()]
        conv_key = RedisKeys.conversation_members(conversation_id)
        async with r.pipeline() as pipe:
            pipe.delete(conv_key)
            if user_ids:
                pipe.sadd(conv_key,*user_ids)
                for user_id in user_ids:
                    pipe.sadd(
                        RedisKeys.user_conversations(user_id),
                        conversation_id
                    )
            await pipe.execute()

    @classmethod
    async def sync_all(cls, db):
        result = await db.execute(
            select(
                ConversationParticipant.conversation_id,
                ConversationParticipant.user_id
            )
        )

        participants = result.all()

        from collections import defaultdict
        conv_map = defaultdict(list)
        user_map = defaultdict(list)

        for row in participants:
            conv_map[str(row.conversation_id)].append(str(row.user_id))
            user_map[str(row.user_id)].append(str(row.conversation_id))

        async with r.pipeline() as pipe:
            for conv_id, users in conv_map.items():
                conv_key = RedisKeys.conversation_members(conv_id)
                pipe.delete(conv_key)
                pipe.sadd(conv_key, *users)

            for user_id, convs in user_map.items():
                user_key = RedisKeys.user_conversations(user_id)
                pipe.delete(user_key)
                pipe.sadd(user_key, *convs)

            await pipe.execute()

        return {
            "conversations_synced": len(conv_map),
            "users_synced": len(user_map),
            "participants_synced": len(participants),
        }


conversation_cache = ConversationCache()