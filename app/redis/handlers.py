import json
from app.redis_client import r
from app.services.cache_management.conversation import conversation_cache
from app.services.cache_management.presence import presence_cache
from app.ws.manager import manager

async def handle_presence(payload: dict):
    target_user_id = payload["user_id"]

    watchers = await presence_cache.watchers(target_user_id)

    for watcher in watchers:
        watcher_id = watcher.decode() if isinstance(watcher, bytes) else str(watcher)
        await manager.send_to_user(watcher_id, payload)

async def conversation_handler(channel:str, data:dict):
    conversation_id = channel.split(":")[1]
    user_ids = manager.get_local_members(conversation_id)
    for uid in user_ids:
        await manager.send_to_user(uid,data)

async def user_handler(channel:str, data:dict):
    user_id = channel.split(":")[1]
    await manager.send_to_user(user_id,data)