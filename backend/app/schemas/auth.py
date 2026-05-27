from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """登录请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    """刷新、退出接口共用的 refresh token 请求体。"""

    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    """当前用户修改密码请求体。"""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class TokenPairResponse(BaseModel):
    """登录或刷新成功后返回的令牌对。"""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    must_change_password: bool
