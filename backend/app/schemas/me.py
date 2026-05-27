from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CurrentUserSummary(BaseModel):
    id: int
    username: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool


class CurrentUserRoleSummary(BaseModel):
    id: int
    name: str
    code: str


class MenuNode(BaseModel):
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
    user: CurrentUserSummary
    roles: list[CurrentUserRoleSummary]
    permissions: list[str]
    menus: list[MenuNode]
    must_change_password: bool


MenuNode.model_rebuild()
