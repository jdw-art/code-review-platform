from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.schemas.permission import (
    PermissionCreateRequest,
    PermissionResponse,
    PermissionUpdateRequest,
)
from app.security.deps import require_permission
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission("permission:read"))],
    summary="获取权限列表",
    description="返回系统中的权限定义列表。需要 `permission:read` 权限。",
)
async def list_permissions(service: RBACService = Depends()) -> list[PermissionResponse]:
    """查询权限列表。"""
    return await service.list_permissions()


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("permission:create"))],
    summary="创建权限",
    description="创建新的权限定义。需要 `permission:create` 权限。",
)
async def create_permission(
    payload: PermissionCreateRequest,
    service: RBACService = Depends(),
) -> PermissionResponse:
    """创建新的权限定义。"""
    return await service.create_permission(payload)


@router.patch(
    "/{permission_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission("permission:update"))],
    summary="更新权限",
    description="更新指定权限的名称、编码、资源或动作。需要 `permission:update` 权限。",
)
async def update_permission(
    permission_id: int,
    payload: PermissionUpdateRequest,
    service: RBACService = Depends(),
) -> PermissionResponse:
    """更新指定权限。"""
    return await service.update_permission(permission_id, payload)


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("permission:delete"))],
    summary="删除权限",
    description="删除指定权限。系统内置权限不允许删除。需要 `permission:delete` 权限。",
)
async def delete_permission(
    permission_id: int,
    service: RBACService = Depends(),
) -> Response:
    """删除指定权限。"""
    await service.delete_permission(permission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
