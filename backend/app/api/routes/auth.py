from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.db.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.security.deps import get_current_user
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="使用用户名和密码登录，返回 access token、refresh token，以及是否需要强制修改密码的状态。",
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(),
) -> TokenPairResponse:
    """处理用户名密码登录请求。"""
    return await service.login(payload)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
    summary="刷新令牌",
    description="使用有效的 refresh token 换取新的 access token 和 refresh token，并执行刷新令牌轮换。",
)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(),
) -> TokenPairResponse:
    """刷新当前会话的令牌对。"""
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出当前会话",
    description="注销当前 refresh token 对应的登录会话，令该会话后续无法继续刷新令牌。",
)
async def logout(
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """注销当前会话。"""
    await service.logout(current_user, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出全部会话",
    description="注销当前用户的所有 refresh token 会话，常用于账号安全加固或主动下线全部设备。",
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """注销当前用户的全部会话。"""
    await service.logout_all(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改当前用户密码",
    description="校验当前密码后更新为新密码，并吊销该用户现有的全部 refresh token 会话。首次登录强制改密场景下可使用该接口解除限制。",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """修改当前登录用户的密码。"""
    await service.change_password(current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
