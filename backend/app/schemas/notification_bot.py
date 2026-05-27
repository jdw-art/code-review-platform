from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationBotResponse(BaseModel):
    """通知机器人接口统一响应模型，敏感 Secret 仅返回掩码。"""

    id: int
    name: str
    bot_type: str
    webhook_url: str
    secret_masked: str | None = None
    mention_strategy: str | None = None
    template_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    last_test_status: str | None = None
    last_test_message: str | None = None
    last_test_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NotificationBotCreateRequest(BaseModel):
    """创建通知机器人请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bot_type: str = Field(min_length=1, max_length=50)
    webhook_url: str = Field(min_length=1)
    secret: str | None = Field(default=None, min_length=1)
    mention_strategy: str | None = Field(default=None, max_length=50)
    template_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class NotificationBotUpdateRequest(BaseModel):
    """更新通知机器人请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bot_type: str = Field(min_length=1, max_length=50)
    webhook_url: str = Field(min_length=1)
    secret: str | None = Field(default=None, min_length=1)
    mention_strategy: str | None = Field(default=None, max_length=50)
    template_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class NotificationBotStatusUpdateRequest(BaseModel):
    """通知机器人启停状态更新请求体。"""

    is_active: bool
