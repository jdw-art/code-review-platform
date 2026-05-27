from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserRoleSummary(BaseModel):
    """用户响应中使用的角色摘要。"""

    id: int
    name: str
    code: str


class UserResponse(BaseModel):
    """用户接口统一响应模型。"""

    id: int
    username: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    roles: list[UserRoleSummary] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    """创建用户请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    nickname: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    is_superuser: bool = False
    role_ids: list[int] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    """更新用户资料请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    nickname: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    is_superuser: bool | None = None


class UserStatusUpdateRequest(BaseModel):
    """用户启用状态更新请求体。"""

    is_active: bool


class UserResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求体。"""

    new_password: str = Field(min_length=8)


class UserRoleAssignRequest(BaseModel):
    """用户角色分配请求体。"""

    role_ids: list[int] = Field(default_factory=list)
