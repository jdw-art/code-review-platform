from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.schemas.menu import MenuCreateRequest, MenuResponse, MenuUpdateRequest
from app.security.deps import require_permission
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/menus", tags=["menus"])


@router.get(
    "",
    response_model=list[MenuResponse],
    dependencies=[Depends(require_permission("menu:read"))],
    summary="获取菜单列表",
    description="返回系统中的菜单平铺列表。需要 `menu:read` 权限。",
)
async def list_menus(service: RBACService = Depends()) -> list[MenuResponse]:
    """查询菜单平铺列表。"""
    return await service.list_menus()


@router.get(
    "/tree",
    response_model=list[MenuResponse],
    dependencies=[Depends(require_permission("menu:read"))],
    summary="获取菜单树",
    description="返回按照父子层级组装完成的菜单树结构。需要 `menu:read` 权限。",
)
async def list_menu_tree(service: RBACService = Depends()) -> list[MenuResponse]:
    """查询菜单树结构。"""
    return await service.list_menu_tree()


@router.post(
    "",
    response_model=MenuResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("menu:create"))],
    summary="创建菜单",
    description="创建新的菜单节点，可指定父级菜单。需要 `menu:create` 权限。",
)
async def create_menu(
    payload: MenuCreateRequest,
    service: RBACService = Depends(),
) -> MenuResponse:
    """创建新的菜单节点。"""
    return await service.create_menu(payload)


@router.patch(
    "/{menu_id}",
    response_model=MenuResponse,
    dependencies=[Depends(require_permission("menu:update"))],
    summary="更新菜单",
    description="更新指定菜单的名称、路径、父级或展示属性。需要 `menu:update` 权限。",
)
async def update_menu(
    menu_id: int,
    payload: MenuUpdateRequest,
    service: RBACService = Depends(),
) -> MenuResponse:
    """更新指定菜单。"""
    return await service.update_menu(menu_id, payload)


@router.delete(
    "/{menu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("menu:delete"))],
    summary="删除菜单",
    description="删除指定菜单。系统内置菜单不允许删除。需要 `menu:delete` 权限。",
)
async def delete_menu(menu_id: int, service: RBACService = Depends()) -> Response:
    """删除指定菜单。"""
    await service.delete_menu(menu_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
