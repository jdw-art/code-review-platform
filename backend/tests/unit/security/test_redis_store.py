import pytest

from app.security.redis_store import RefreshSessionStore


class FakeRedis:
    def __init__(self) -> None:
        self.string_values: dict[str, str] = {}
        self.set_values: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.string_values[key] = value
        self.ttls[key] = ttl_seconds

    async def get(self, key: str) -> str | None:
        return self.string_values.get(key)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.string_values:
                del self.string_values[key]
                self.ttls.pop(key, None)
                deleted += 1
            if key in self.set_values:
                del self.set_values[key]
                self.ttls.pop(key, None)
                deleted += 1
        return deleted

    async def sadd(self, key: str, value: str) -> None:
        members = self.set_values.setdefault(key, set())
        members.add(value)

    async def srem(self, key: str, value: str) -> None:
        members = self.set_values.get(key)
        if not members:
            return
        members.discard(value)
        if not members:
            self.set_values.pop(key, None)
            self.ttls.pop(key, None)

    async def smembers(self, key: str) -> set[str]:
        return set(self.set_values.get(key, set()))

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        if key not in self.string_values and key not in self.set_values:
            return False
        self.ttls[key] = ttl_seconds
        return True


@pytest.mark.anyio
async def test_refresh_session_store_manages_session_lifecycle() -> None:
    redis = FakeRedis()
    store = RefreshSessionStore(redis)

    await store.save_refresh_session("jti-123", user_id=7, ttl_seconds=3600)

    assert await store.get_user_id_for_session("jti-123") == 7
    assert await store.list_user_session_jtis(user_id=7) == {"jti-123"}
    assert redis.ttls["auth:refresh:jti-123"] == 3600
    assert redis.ttls["auth:user_refresh_index:7"] == 3600

    await store.revoke_refresh_session("jti-123", user_id=7)

    assert await store.get_user_id_for_session("jti-123") is None
    assert await store.list_user_session_jtis(user_id=7) == set()


@pytest.mark.anyio
async def test_refresh_session_store_can_revoke_all_user_sessions() -> None:
    redis = FakeRedis()
    store = RefreshSessionStore(redis)

    await store.save_refresh_session("jti-1", user_id=7, ttl_seconds=3600)
    await store.save_refresh_session("jti-2", user_id=7, ttl_seconds=3600)

    revoked = await store.revoke_all_user_sessions(user_id=7)

    assert revoked == 2
    assert await store.get_user_id_for_session("jti-1") is None
    assert await store.get_user_id_for_session("jti-2") is None
    assert await store.list_user_session_jtis(user_id=7) == set()
