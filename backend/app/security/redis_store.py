from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisClientProtocol(Protocol):
    async def setex(self, key: str, ttl_seconds: int, value: str) -> None: ...
    async def get(self, key: str) -> str | bytes | None: ...
    async def delete(self, *keys: str) -> int: ...
    async def sadd(self, key: str, value: str) -> None: ...
    async def srem(self, key: str, value: str) -> None: ...
    async def smembers(self, key: str) -> set[str] | set[bytes]: ...
    async def expire(self, key: str, ttl_seconds: int) -> bool: ...


class RefreshSessionStore:
    def __init__(self, redis_client: "Redis | RedisClientProtocol") -> None:
        self.redis = redis_client

    async def save_refresh_session(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        await self.redis.setex(self._session_key(jti), ttl_seconds, str(user_id))
        index_key = self._user_index_key(user_id)
        await self.redis.sadd(index_key, jti)
        await self.redis.expire(index_key, ttl_seconds)

    async def get_user_id_for_session(self, jti: str) -> int | None:
        value = await self.redis.get(self._session_key(jti))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode()
        return int(value)

    async def list_user_session_jtis(self, user_id: int) -> set[str]:
        values = await self.redis.smembers(self._user_index_key(user_id))
        return {
            value.decode() if isinstance(value, bytes) else value
            for value in values
        }

    async def revoke_refresh_session(self, jti: str, user_id: int) -> None:
        await self.redis.delete(self._session_key(jti))
        await self.redis.srem(self._user_index_key(user_id), jti)

    async def revoke_all_user_sessions(self, user_id: int) -> int:
        session_jtis = await self.list_user_session_jtis(user_id)
        if not session_jtis:
            return 0

        session_keys = [self._session_key(jti) for jti in session_jtis]
        await self.redis.delete(*session_keys)
        await self.redis.delete(self._user_index_key(user_id))
        return len(session_jtis)

    @staticmethod
    def _session_key(jti: str) -> str:
        return f"auth:refresh:{jti}"

    @staticmethod
    def _user_index_key(user_id: int) -> str:
        return f"auth:user_refresh_index:{user_id}"
