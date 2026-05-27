from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.menu import MenuResponse
from app.schemas.permission import PermissionResponse


class RoleResponse(BaseModel):
    """角色接口统一响应模型。"""

    id: int
    name: str
    code: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionResponse] = Field(default_factory=list)
    menus: list[MenuResponse] = Field(default_factory=list)


class RoleCreateRequest(BaseModel):
    """创建角色请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RoleUpdateRequest(BaseModel):
    """更新角色请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionAssignRequest(BaseModel):
    """角色权限分配请求体。"""

    permission_ids: list[int] = Field(default_factory=list)


class RoleMenuAssignRequest(BaseModel):
    """角色菜单分配请求体。"""

    menu_ids: list[int] = Field(default_factory=list)
