from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.models import User
from app.schemas.me import AccessContextResponse, CurrentUserProfileResponse
from app.security.deps import get_current_user
from app.services.access_context import AccessContextService


router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "/access-context",
    response_model=AccessContextResponse,
    summary="获取当前用户访问上下文",
    description="返回当前用户的基础信息、角色列表、权限编码列表、菜单树以及是否需要强制修改密码，供前端初始化权限与导航使用。",
)
async def get_access_context(
    current_user: User = Depends(get_current_user),
    service: AccessContextService = Depends(),
) -> AccessContextResponse:
    """获取当前用户的权限与菜单上下文。"""
    return await service.get_access_context(current_user)


@router.get(
    "/profile",
    response_model=CurrentUserProfileResponse,
    summary="获取当前用户资料",
    description="返回当前登录用户的资料摘要和角色信息。该接口在首次登录强制改密期间仍允许访问。",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    service: AccessContextService = Depends(),
) -> CurrentUserProfileResponse:
    """获取当前用户的资料信息。"""
    return await service.get_profile(current_user)
