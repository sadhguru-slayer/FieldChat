import time
from app.redis_client import r
from app.redis.keys import RedisKeys

class PresenceCache:
    @staticmethod
    async def watch(watcher_id:str, target_user_id:str):
        return await r.sadd(
            RedisKeys.presence_watchers(target_user_id),
            watcher_id
        )
    
    @staticmethod
    async def unwatch(watcher_id:str, target_user_id:str):
        await r.srem(
            RedisKeys.presence_watchers(target_user_id),
            watcher_id
        )

    @staticmethod
    async def online(target_user_id:str):
        return await r.sismember(
            RedisKeys.online_users(),
            target_user_id
        )
    
    @staticmethod
    async def watchers(target_user_id:str):
        return await r.smembers(
            RedisKeys.presence_watchers(target_user_id)
        )

    @staticmethod
    async def set_offline(user_id: str):
        """Remove from online set and stamp last-seen timestamp."""
        await r.srem(
            RedisKeys.online_users(),
            user_id,
        )
        await r.set(
            RedisKeys.last_seen(user_id),
            int(time.time()),
        )

    @staticmethod
    async def get_last_seen(user_id: str) -> int | None:
        """Return Unix timestamp (seconds) of last seen, or None if never set."""
        value = await r.get(RedisKeys.last_seen(user_id))
        return int(value) if value is not None else None

presence_cache = PresenceCache()