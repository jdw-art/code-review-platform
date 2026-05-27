from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.db.models import User
from app.schemas.role import (
    RoleCreateRequest,
    RoleMenuAssignRequest,
    RolePermissionAssignRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.security.deps import require_permission
from app.services.audit_log_service import AuditLogService
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permission("role:read"))],
    summary="获取角色列表",
    description="返回系统中的角色列表，以及每个角色关联的权限与菜单摘要。需要 `role:read` 权限。",
)
async def list_roles(service: RBACService = Depends()) -> list[RoleResponse]:
    """查询角色列表。"""
    return await service.list_roles()


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("role:read"))],
    summary="获取角色详情",
    description="根据角色 ID 查询角色详情，包括已绑定的权限与菜单。需要 `role:read` 权限。",
)
async def get_role(role_id: int, service: RBACService = Depends()) -> RoleResponse:
    """查询单个角色详情。"""
    return await service.get_role(role_id)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
    description="创建新的角色定义。需要 `role:create` 权限。",
)
async def create_role(
    request: Request,
    payload: RoleCreateRequest,
    current_user: User = Depends(require_permission("role:create")),
    service: RBACService = Depends(),
) -> RoleResponse:
    """创建新的角色。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="create",
        resource_type="role",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_role(current_user, payload, audit_context)


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="更新角色",
    description="更新指定角色的名称或描述。需要 `role:update` 权限。",
)
async def update_role(
    request: Request,
    role_id: int,
    payload: RoleUpdateRequest,
    current_user: User = Depends(require_permission("role:update")),
    service: RBACService = Depends(),
) -> RoleResponse:
    """更新角色的展示信息。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="update",
        resource_type="role",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_role(current_user, role_id, payload, audit_context)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除角色",
    description="删除指定角色。系统内置角色不允许删除。需要 `role:delete` 权限。",
)
async def delete_role(
    request: Request,
    role_id: int,
    current_user: User = Depends(require_permission("role:delete")),
    service: RBACService = Depends(),
) -> Response:
    """删除指定角色。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="delete",
        resource_type="role",
        response_status=status.HTTP_204_NO_CONTENT,
    )
    await service.delete_role(current_user, role_id, audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{role_id}/permissions",
    response_model=RoleResponse,
    summary="分配角色权限",
    description="使用权限 ID 列表覆盖指定角色当前的权限集合。需要 `role:assign` 权限。",
)
async def assign_role_permissions(
    request: Request,
    role_id: int,
    payload: RolePermissionAssignRequest,
    current_user: User = Depends(require_permission("role:assign")),
    service: RBACService = Depends(),
) -> RoleResponse:
    """为角色分配权限集合。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="assign-permission",
        resource_type="role",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.assign_permissions(current_user, role_id, payload, audit_context)


@router.put(
    "/{role_id}/menus",
    response_model=RoleResponse,
    summary="分配角色菜单",
    description="使用菜单 ID 列表覆盖指定角色当前可见的菜单集合。需要 `role:assign` 权限。",
)
async def assign_role_menus(
    request: Request,
    role_id: int,
    payload: RoleMenuAssignRequest,
    current_user: User = Depends(require_permission("role:assign")),
    service: RBACService = Depends(),
) -> RoleResponse:
    """为角色分配菜单集合。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="assign-menu",
        resource_type="role",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.assign_menus(current_user, role_id, payload, audit_context)
