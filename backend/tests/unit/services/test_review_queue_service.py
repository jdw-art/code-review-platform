import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.integration_webhook import ReviewQueueMessage
from app.services.review_queue_service import ReviewQueueService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, list[str]] = {}
        self.string_values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def rpush(self, key: str, value: str) -> int:
        items = self.values.setdefault(key, [])
        items.append(value)
        return len(items)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self.string_values:
            return None
        self.string_values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.mark.anyio
async def test_queue_service_pushes_minimal_message(fake_redis: FakeRedis) -> None:
    service = ReviewQueueService(redis_client=fake_redis, queue_name="review:jobs")

    await service.enqueue(review_record_id=101, platform_type="gitlab", attempt=1)

    assert fake_redis.values["review:jobs"] == [
        '{"review_record_id":101,"platform_type":"gitlab","attempt":1}'
    ]


@pytest.mark.anyio
async def test_queue_service_acquires_processing_lock(fake_redis: FakeRedis) -> None:
    service = ReviewQueueService(
        redis_client=fake_redis,
        queue_name="review:jobs",
        lock_prefix="review:lock",
    )

    assert await service.acquire_lock(review_record_id=7, ttl_seconds=30) is True
    assert await service.acquire_lock(review_record_id=7, ttl_seconds=30) is False
    assert fake_redis.ttls["review:lock:7"] == 30


def test_review_queue_message_rejects_unknown_platform_type() -> None:
    with pytest.raises(ValidationError, match="platform_type"):
        ReviewQueueMessage(
            review_record_id=101,
            platform_type="gitea",
            attempt=1,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("review_queue_name", ""),
        ("review_lock_prefix", ""),
        ("review_max_retries", -1),
        ("review_lock_ttl_seconds", 0),
    ],
)
def test_settings_validate_review_queue_boundaries(
    field_name: str,
    field_value: str | int,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        Settings(**{field_name: field_value})
