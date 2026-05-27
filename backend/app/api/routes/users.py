from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.db.models import User
from app.schemas.user import (
    UserCreateRequest,
    UserResetPasswordRequest,
    UserResponse,
    UserRoleAssignRequest,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from app.security.deps import get_current_user, require_permission
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission("user:read"))],
    summary="获取用户列表",
    description="返回系统中的用户列表及其角色摘要。需要 `user:read` 权限。",
)
async def list_users(service: UserService = Depends()) -> list[UserResponse]:
    """查询用户列表。"""
    return await service.list_users()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:read"))],
    summary="获取用户详情",
    description="根据用户 ID 查询单个用户的详细信息及角色摘要。需要 `user:read` 权限。",
)
async def get_user(user_id: int, service: UserService = Depends()) -> UserResponse:
    """查询单个用户详情。"""
    return await service.get_user(user_id)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:create"))],
    summary="创建用户",
    description="创建一个新的后台用户，并可在创建时一次性绑定角色。需要 `user:create` 权限。",
)
async def create_user(
    payload: UserCreateRequest,
    service: UserService = Depends(),
) -> UserResponse:
    """创建新的用户账号。"""
    return await service.create_user(payload)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:update"))],
    summary="更新用户资料",
    description="更新指定用户的昵称、邮箱、手机号或超级管理员状态。需要 `user:update` 权限。",
)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_permission("user:update")),
    service: UserService = Depends(),
) -> UserResponse:
    """更新指定用户的资料字段。"""
    return await service.update_user(current_user, user_id, payload)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:status"))],
    summary="修改用户启用状态",
    description="启用或禁用指定用户。禁用用户时会撤销其现有 refresh token 会话。需要 `user:status` 权限。",
)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    current_user: User = Depends(require_permission("user:status")),
    service: UserService = Depends(),
) -> UserResponse:
    """修改用户的启用状态。"""
    return await service.update_status(current_user, user_id, payload)


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:reset-password"))],
    summary="重置用户密码",
    description="管理员为指定用户重置密码，并强制该用户下次登录后立即修改密码。需要 `user:reset-password` 权限。",
)
async def reset_user_password(
    user_id: int,
    payload: UserResetPasswordRequest,
    service: UserService = Depends(),
) -> Response:
    """重置指定用户的密码。"""
    await service.reset_password(user_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{user_id}/roles",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:assign-role"))],
    summary="分配用户角色",
    description="使用角色 ID 列表覆盖指定用户当前的角色集合。需要 `user:assign-role` 权限。",
)
async def assign_user_roles(
    user_id: int,
    payload: UserRoleAssignRequest,
    service: UserService = Depends(),
) -> UserResponse:
    """为指定用户分配角色。"""
    return await service.assign_roles(user_id, payload)
