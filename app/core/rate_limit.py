import time
from fastapi import HTTPException, Request
from app.redis_client import r

def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")

class RedisRateLimiter:
    def __init__(self, limit: int, window_seconds: int, key_prefix: str = "global"):
        """
        :param limit: Maximum allowed requests in the window.
        :param window_seconds: Time window duration in seconds.
        :param key_prefix: Unique identifier for this limit scope.
        """
        self.limit = limit
        self.window = window_seconds
        self.key_prefix = key_prefix

    async def check_rate_limit(self, identifier: str) -> None:
        """
        Executes the sliding window rate limit checks in Redis for the given identifier.
        Raises HTTPException(429) if the limit is exceeded.
        """
        key = f"ratelimit:{self.key_prefix}:{identifier}"
        now = time.time()
        clear_before = now - self.window

        # Pipeline executes multiple commands atomically in a single network round-trip
        async with r.pipeline(transaction=True) as pipe:
            # 1. Remove request logs older than the sliding window boundary
            pipe.zremrangebyscore(key, 0, clear_before)
            # 2. Count the remaining active request logs in the window
            pipe.zcard(key)
            # 3. Log the current request timestamp
            pipe.zadd(key, {str(now): now})
            # 4. Set sliding window expiry for automatic cleanup of idle keys
            pipe.expire(key, self.window)
            
            results = await pipe.execute()
            current_requests = results[1]

        if current_requests > self.limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )

    async def __call__(self, request: Request):
        # Determine unique client identifier (User ID if authenticated, else IP address)
        identifier = get_client_ip(request)
        if hasattr(request.state, "user") and request.state.user:
            identifier = str(request.state.user.id)
        else:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    from app.core.security.auth import token_manager
                    payload = token_manager.decode_token(token)
                    if payload and payload.get("sub"):
                        identifier = str(payload.get("sub"))
                except Exception:
                    pass

        await self.check_rate_limit(identifier)
