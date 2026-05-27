from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CurrentUserSummary(BaseModel):
    """当前用户访问上下文中的基础资料摘要。"""

    id: int
    username: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool


class CurrentUserRoleSummary(BaseModel):
    """当前用户角色摘要。"""

    id: int
    name: str
    code: str


class MenuNode(BaseModel):
    """前端导航使用的菜单树节点。"""

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
    children: list["MenuNode"] = Field(default_factory=list)


class AccessContextResponse(BaseModel):
    """当前用户访问上下文响应模型。"""

    user: CurrentUserSummary
    roles: list[CurrentUserRoleSummary]
    permissions: list[str]
    menus: list[MenuNode]
    must_change_password: bool


class CurrentUserProfileResponse(BaseModel):
    """当前用户资料响应模型。"""

    id: int
    username: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    roles: list[CurrentUserRoleSummary]


MenuNode.model_rebuild()
