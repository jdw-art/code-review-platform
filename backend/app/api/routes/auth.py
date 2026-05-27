from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.db.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.schemas.common import DomainError
from app.security.deps import get_current_user
from app.services.audit_log_service import AuditLogService
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
    request: Request,
    payload: LoginRequest,
    service: AuthService = Depends(),
    audit_service: AuditLogService = Depends(),
) -> TokenPairResponse:
    """处理用户名密码登录请求。"""
    audit_context = AuditLogService.build_context(
        request=request,
        username=payload.username,
        action="login",
        resource_type="auth",
        resource_name=payload.username,
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    try:
        return await service.login(payload, audit_context)
    except DomainError as exc:
        audit_service.record_action(
            AuditLogService.build_context(
                request=request,
                username=payload.username,
                action="login",
                resource_type="auth",
                payload=payload,
                response_status=exc.status_code,
                result="failure",
                error_message=exc.message,
            ),
            commit=True,
        )
        raise


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
    request: Request,
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """注销当前会话。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="logout",
        resource_type="auth",
        resource_id=current_user.id,
        resource_name=current_user.username,
        payload=payload,
        response_status=status.HTTP_204_NO_CONTENT,
    )
    await service.logout(current_user, payload.refresh_token, audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出全部会话",
    description="注销当前用户的所有 refresh token 会话，常用于账号安全加固或主动下线全部设备。",
)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """注销当前用户的全部会话。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="logout-all",
        resource_type="auth",
        resource_id=current_user.id,
        resource_name=current_user.username,
        response_status=status.HTTP_204_NO_CONTENT,
    )
    await service.logout_all(current_user, audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改当前用户密码",
    description="校验当前密码后更新为新密码，并吊销该用户现有的全部 refresh token 会话。首次登录强制改密场景下可使用该接口解除限制。",
)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    """修改当前登录用户的密码。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="change-password",
        resource_type="auth",
        resource_id=current_user.id,
        resource_name=current_user.username,
        payload=payload,
        response_status=status.HTTP_204_NO_CONTENT,
    )
    await service.change_password(current_user, payload, audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
