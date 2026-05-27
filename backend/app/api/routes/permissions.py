from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.db.models import User
from app.schemas.permission import (
    PermissionCreateRequest,
    PermissionResponse,
    PermissionUpdateRequest,
)
from app.security.deps import require_permission
from app.services.audit_log_service import AuditLogService
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
    summary="创建权限",
    description="创建新的权限定义。需要 `permission:create` 权限。",
)
async def create_permission(
    request: Request,
    payload: PermissionCreateRequest,
    current_user: User = Depends(require_permission("permission:create")),
    service: RBACService = Depends(),
) -> PermissionResponse:
    """创建新的权限定义。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="permission.create",
        resource_type="permission",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_permission(current_user, payload, audit_context)


@router.patch(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="更新权限",
    description="更新指定权限的名称、编码、资源或动作。需要 `permission:update` 权限。",
)
async def update_permission(
    request: Request,
    permission_id: int,
    payload: PermissionUpdateRequest,
    current_user: User = Depends(require_permission("permission:update")),
    service: RBACService = Depends(),
) -> PermissionResponse:
    """更新指定权限。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="permission.update",
        resource_type="permission",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_permission(current_user, permission_id, payload, audit_context)


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除权限",
    description="删除指定权限。系统内置权限不允许删除。需要 `permission:delete` 权限。",
)
async def delete_permission(
    request: Request,
    permission_id: int,
    current_user: User = Depends(require_permission("permission:delete")),
    service: RBACService = Depends(),
) -> Response:
    """删除指定权限。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="permission.delete",
        resource_type="permission",
        response_status=status.HTTP_204_NO_CONTENT,
    )
    await service.delete_permission(current_user, permission_id, audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
