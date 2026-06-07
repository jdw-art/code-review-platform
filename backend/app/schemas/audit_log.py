from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class AuditActionContext:
    """一次后台变更动作的审计上下文。"""

    action: str
    resource_type: str
    user_id: int | None = None
    username: str | None = None
    resource_id: int | None = None
    resource_name: str | None = None
    request_path: str | None = None
    request_method: str | None = None
    request_payload: dict[str, Any] = field(default_factory=dict)
    response_status: int | None = None
    result: str = "success"
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    def with_resource(
        self,
        *,
        resource_id: int | None = None,
        resource_name: str | None = None,
        resource_name_snapshot: str | None = None,
        response_status: int | None = None,
        request_payload: dict[str, Any] | None = None,
        result: str | None = None,
        error_message: str | None = None,
    ) -> "AuditActionContext":
        """在保留请求元数据的前提下补齐资源信息。"""
        next_resource_name = resource_name if resource_name is not None else resource_name_snapshot
        return replace(
            self,
            resource_id=resource_id if resource_id is not None else self.resource_id,
            resource_name=next_resource_name if next_resource_name is not None else self.resource_name,
            response_status=response_status if response_status is not None else self.response_status,
            request_payload=request_payload if request_payload is not None else self.request_payload,
            result=result if result is not None else self.result,
            error_message=error_message if error_message is not None else self.error_message,
        )


class AuditLogResponse(BaseModel):
    """审计日志接口统一响应模型。"""

    id: int
    user_id: int | None = None
    username_snapshot: str | None = None
    action: str
    resource_type: str
    resource_id: int | None = None
    resource_name_snapshot: str | None = None
    request_path: str | None = None
    request_method: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_status: int | None = None
    result: str | None = None
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogQuery(BaseModel):
    """审计日志列表查询参数。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    action: str | None = Field(default=None, max_length=100)
    resource_type: str | None = Field(default=None, max_length=100)
    user_id: int | None = None
    result: str | None = Field(default=None, max_length=32)

    @property
    def offset(self) -> int:
        """返回 SQL 查询所需的偏移量。"""
        return (self.page - 1) * self.page_size


class AuditLogPurgeResponse(BaseModel):
    """审计日志清理响应。"""

    purged_count: int
