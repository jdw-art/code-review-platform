from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    """权限接口统一响应模型。"""

    id: int
    name: str
    code: str
    resource: str
    action: str
    description: str | None = None
    is_system: bool


class PermissionCreateRequest(BaseModel):
    """创建权限请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class PermissionUpdateRequest(BaseModel):
    """更新权限请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=100)
    resource: str | None = Field(default=None, max_length=100)
    action: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)
