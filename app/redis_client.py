import redis.asyncio as redis
r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    socket_timeout=None,
    socket_connect_timeout=5,
)