from app.redis_client import r
from app.redis.keys import RedisKeys

class PresenceCache:
    @staticmethod
    async def watch(watcher_id:str, target_user_id:str):
        return r.sadd(
            RedisKeys.presence_watchers(target_user_id),
            watcher_id
        )
    
    @staticmethod
    async def unwatch(watcher_id:str, target_user_id:str):
        r.srem(
            RedisKeys.presence_watchers(target_user_id),
            watcher_id
        )
    @staticmethod
    async def online(target_user_id:str):
        return r.sismember(
            RedisKeys.online_users(),
            target_user_id
        )
    
    @staticmethod
    async def watchers(target_user_id:str):
        return r.smembers(
            RedisKeys.presence_watchers(target_user_id)
        )

presence_cache = PresenceCache()