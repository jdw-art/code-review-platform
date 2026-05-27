from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.common import DomainForbiddenError, DomainUnauthorizedError
from app.security.tokens import TokenError, decode_token
from app.services.access_context import AccessContextService


bearer_scheme = HTTPBearer(auto_error=False)
# 首次登录强制改密期间，仅允许访问不会扩大权限面的安全接口。
PASSWORD_CHANGE_ALLOWED_PATHS = {
    "/api/v1/auth/change-password",
    "/api/v1/auth/logout",
    "/api/v1/auth/logout-all",
    "/api/v1/me/profile",
}


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    """解析 access token 并返回当前有效用户。"""
    if credentials is None:
        raise DomainUnauthorizedError(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication required.",
        )

    try:
        claims = decode_token(credentials.credentials, expected_token_type="access")
    except TokenError as exc:
        raise DomainUnauthorizedError(
            code="INVALID_ACCESS_TOKEN",
            message="Invalid or expired access token.",
        ) from exc
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DomainUnauthorizedError(
            code="INVALID_ACCESS_TOKEN",
            message="Invalid or expired access token.",
        ) from exc

    user = session.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise DomainUnauthorizedError(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication required.",
        )
    # 如果用户仍处于强制改密阶段，则限制其只能访问白名单接口。
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_ALLOWED_PATHS:
        raise DomainForbiddenError(
            code="PASSWORD_CHANGE_REQUIRED",
            message="Password change required.",
        )
    request.state.current_user = user
    return user


def require_permission(permission_code: str) -> Callable[..., User]:
    """构造一个基于权限编码的路由依赖。"""
    async def dependency(
        current_user: User = Depends(get_current_user),
        access_context_service: AccessContextService = Depends(),
    ) -> User:
        # 超级管理员天然拥有全量权限，其余用户走角色聚合后的权限集合校验。
        permission_codes = await access_context_service.get_permission_codes(current_user.id)
        if not current_user.is_superuser and permission_code not in permission_codes:
            raise DomainForbiddenError(
                code="FORBIDDEN",
                message="Forbidden.",
            )
        return current_user

    return dependency
