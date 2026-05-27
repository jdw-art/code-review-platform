from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MenuResponse(BaseModel):
    """菜单接口统一响应模型。"""

    id: int
    parent_id: int | None = None
    name: str
    path: str
    component: str | None = None
    icon: str | None = None
    sort: int
    visible: bool
    redirect: str | None = None
    meta: dict[str, Any] | None = None
    is_system: bool
    children: list["MenuResponse"] = Field(default_factory=list)


class MenuCreateRequest(BaseModel):
    """创建菜单请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=100)
    path: str = Field(min_length=1, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    sort: int = 0
    visible: bool = True
    redirect: str | None = Field(default=None, max_length=255)
    meta: dict[str, Any] | None = None


class MenuUpdateRequest(BaseModel):
    """更新菜单请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    parent_id: int | None = None
    name: str | None = Field(default=None, max_length=100)
    path: str | None = Field(default=None, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=100)
    sort: int | None = None
    visible: bool | None = None
    redirect: str | None = Field(default=None, max_length=255)
    meta: dict[str, Any] | None = None


MenuResponse.model_rebuild()
