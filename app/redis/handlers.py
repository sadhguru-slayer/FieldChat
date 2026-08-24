import json
from app.redis_client import r
from app.services.cache_management.conversation import conversation_cache
from app.ws.manager import manager

async def conversation_handler(channel:str, data:dict):
    conversation_id = channel.split(":")[1]
    user_ids = manager.get_local_members(conversation_id)
    for uid in user_ids:
        await manager.send_to_user(uid,data)

async def user_handler(channel:str, data:dict):
    user_id = channel.split(":")[1]
    await manager.send_to_user(user_id,data)