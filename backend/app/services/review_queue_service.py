from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Literal, Protocol

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import Settings
from app.schemas.integration_webhook import ReviewQueueMessage
from app.services.auth_service import get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis as AsyncRedis


class ReviewQueueRedisProtocol(Protocol):
    async def rpush(self, key: str, value: str) -> int: ...
    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None: ...


@lru_cache
def get_review_queue_redis_client() -> Redis:
    """创建并缓存 review queue 使用的 Redis 客户端。"""
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


class ReviewQueueService:
    """封装审查任务的入队与基础处理锁能力。"""

    def __init__(
        self,
        redis_client: "AsyncRedis | ReviewQueueRedisProtocol",
        queue_name: str,
        lock_prefix: str = "review:lock",
    ) -> None:
        self.redis = redis_client
        self.queue_name = queue_name
        self.lock_prefix = lock_prefix

    async def enqueue(
        self,
        *,
        review_record_id: int,
        platform_type: Literal["gitlab", "github"],
        attempt: int = 1,
    ) -> None:
        message = ReviewQueueMessage(
            review_record_id=review_record_id,
            platform_type=platform_type,
            attempt=attempt,
        )
        await self.redis.rpush(self.queue_name, message.model_dump_json())

    async def acquire_lock(self, *, review_record_id: int, ttl_seconds: int) -> bool:
        result = await self.redis.set(
            self._lock_key(review_record_id),
            "1",
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    def _lock_key(self, review_record_id: int) -> str:
        return f"{self.lock_prefix}:{review_record_id}"


def get_review_queue_service(
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_review_queue_redis_client),
) -> ReviewQueueService:
    """构造审查任务队列服务。"""
    return ReviewQueueService(
        redis_client=redis_client,
        queue_name=settings.review_queue_name,
        lock_prefix=settings.review_lock_prefix,
    )
