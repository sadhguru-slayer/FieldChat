import json
from app.redis_client import r
from app.redis.handlers import conversation_handler, user_handler, handle_presence
from app.ws.manager import manager

async def start_redis_listener():
    pubsub = r.pubsub()

    await pubsub.psubscribe("conversation:*", "user:*", "presence")

    async for message in pubsub.listen():
        try:
            if message["type"] != "pmessage":
                continue

            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()

            raw = message["data"]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            payload = json.loads(raw)

            if channel.startswith("conversation:"):
                await conversation_handler(channel, payload)
            elif channel.startswith("user:"):
                await user_handler(channel, payload)
            elif channel == "presence":
                await handle_presence(payload)
        except Exception as e:
            print(f"[Redis Listener Error] {e}")

