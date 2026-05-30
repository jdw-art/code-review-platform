from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WebhookAcceptedResponse(BaseModel):
    """webhook 入队响应模型。"""

    review_record_id: int
    status: Literal["queued", "duplicate", "skipped"]


class ReviewQueueMessage(BaseModel):
    """Redis 审查队列消息模型。"""

    review_record_id: int
    platform_type: Literal["gitlab", "github"]
    attempt: int = 1
