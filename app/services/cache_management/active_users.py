from app.redis_client import r

class ActiveUsersCache:
    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"conversation:{conversation_id}:active_users"

    @classmethod
    async def add_active_user(cls, conversation_id: str, user_id: str) -> int:
        """Add a user to the active users set for a conversation."""
        return await r.sadd(cls._key(conversation_id), str(user_id))

    @classmethod
    async def remove_active_user(cls, conversation_id: str, user_id: str) -> int:
        """Remove a user from the active users set for a conversation."""
        return await r.srem(cls._key(conversation_id), str(user_id))

    @classmethod
    async def is_user_active(cls, conversation_id: str, user_id: str) -> bool:
        """Check if a user is actively viewing a conversation."""
        return bool(await r.sismember(cls._key(conversation_id), str(user_id)))

active_users_cache = ActiveUsersCache()
