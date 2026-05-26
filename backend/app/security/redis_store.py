from redis.asyncio import Redis


class RefreshSessionStore:
    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def save_refresh_session(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        await self.redis.setex(f"auth:refresh:{jti}", ttl_seconds, str(user_id))
        await self.redis.sadd(f"auth:user_refresh_index:{user_id}", jti)
