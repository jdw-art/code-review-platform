from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Menu, Permission, Role
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.menu import MenuCreateRequest, MenuResponse, MenuUpdateRequest
from app.schemas.permission import (
    PermissionCreateRequest,
    PermissionResponse,
    PermissionUpdateRequest,
)
from app.schemas.role import (
    RoleCreateRequest,
    RoleMenuAssignRequest,
    RolePermissionAssignRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.services.access_context import build_menu_tree
from app.services.audit_log_service import AuditActionContext, AuditLogService

logger = logging.getLogger(__name__)


class RBACService:
    """封装角色、权限、菜单及其关联关系的管理逻辑。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session
        self.audit_log_service = AuditLogService(session)

    async def list_roles(self) -> list[RoleResponse]:
        """返回角色列表及其权限、菜单摘要。"""
        roles = self.session.scalars(
            select(Role)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.menus),
            )
            .order_by(Role.id.asc())
        ).all()
        return [self._to_role_response(role) for role in roles]

    async def get_role(self, role_id: int) -> RoleResponse:
        """按角色 ID 查询详情。"""
        role = self._get_role_or_404(role_id)
        return self._to_role_response(role)

    async def create_role(
        self,
        current_user,
        payload: RoleCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> RoleResponse:
        """创建新的角色定义。"""
        role = Role(
            name=payload.name,
            code=payload.code,
            description=payload.description,
            is_system=False,
        )
        self.session.add(role)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=role.id,
                    resource_name=role.name,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self.session.commit()
        self.session.refresh(role)
        role = self._get_role_or_404(role.id)
        logger.info("Role created role_id=%s code=%s.", role.id, role.code)
        return self._to_role_response(role)

    async def update_role(
        self,
        current_user,
        role_id: int,
        payload: RoleUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> RoleResponse:
        """更新角色的展示信息。"""
        role = self._get_role_or_404(role_id)
        for field_name, field_value in payload.model_dump(exclude_unset=True).items():
            setattr(role, field_name, field_value)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=role.id,
                    resource_name=role.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(role)
        role = self._get_role_or_404(role.id)
        logger.info("Role updated role_id=%s.", role.id)
        return self._to_role_response(role)

    async def delete_role(
        self,
        current_user,
        role_id: int,
        audit_context: AuditActionContext | None = None,
    ) -> None:
        """删除指定角色。"""
        role = self._get_role_or_404(role_id)
        if role.is_system:
            raise DomainConflictError(
                code="SYSTEM_ROLE_DELETE_FORBIDDEN",
                message="System roles cannot be deleted.",
            )
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=role.id,
                    resource_name=role.name,
                    response_status=status.HTTP_204_NO_CONTENT,
                ),
            )
        self.session.delete(role)
        self.session.commit()
        logger.info("Role deleted role_id=%s.", role_id)

    async def assign_permissions(
        self,
        current_user,
        role_id: int,
        payload: RolePermissionAssignRequest,
        audit_context: AuditActionContext | None = None,
    ) -> RoleResponse:
        """覆盖指定角色当前的权限集合。"""
        role = self._get_role_or_404(role_id)
        role.permissions = self._get_permissions_or_404(payload.permission_ids)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=role.id,
                    resource_name=role.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(role)
        role = self._get_role_or_404(role.id)
        logger.info("Permissions assigned role_id=%s.", role.id)
        return self._to_role_response(role)

    async def assign_menus(
        self,
        current_user,
        role_id: int,
        payload: RoleMenuAssignRequest,
        audit_context: AuditActionContext | None = None,
    ) -> RoleResponse:
        """覆盖指定角色当前的菜单集合。"""
        role = self._get_role_or_404(role_id)
        role.menus = self._get_menus_or_404(payload.menu_ids)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=role.id,
                    resource_name=role.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(role)
        role = self._get_role_or_404(role.id)
        logger.info("Menus assigned role_id=%s.", role.id)
        return self._to_role_response(role)

    async def list_permissions(self) -> list[PermissionResponse]:
        """返回权限定义列表。"""
        permissions = self.session.scalars(
            select(Permission).order_by(Permission.id.asc())
        ).all()
        return [self._to_permission_response(permission) for permission in permissions]

    async def get_permission(self, permission_id: int) -> PermissionResponse:
        """按权限 ID 查询详情。"""
        return self._to_permission_response(self._get_permission_or_404(permission_id))

    async def create_permission(
        self,
        current_user,
        payload: PermissionCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> PermissionResponse:
        """创建新的权限定义。"""
        permission = Permission(
            name=payload.name,
            code=payload.code,
            resource=payload.resource,
            action=payload.action,
            description=payload.description,
            is_system=False,
        )
        self.session.add(permission)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=permission.id,
                    resource_name=permission.code,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self.session.commit()
        self.session.refresh(permission)
        logger.info("Permission created permission_id=%s code=%s.", permission.id, permission.code)
        return self._to_permission_response(permission)

    async def update_permission(
        self,
        current_user,
        permission_id: int,
        payload: PermissionUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> PermissionResponse:
        """更新指定权限。"""
        permission = self._get_permission_or_404(permission_id)
        for field_name, field_value in payload.model_dump(exclude_unset=True).items():
            setattr(permission, field_name, field_value)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=permission.id,
                    resource_name=permission.code,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(permission)
        logger.info("Permission updated permission_id=%s.", permission.id)
        return self._to_permission_response(permission)

    async def delete_permission(
        self,
        current_user,
        permission_id: int,
        audit_context: AuditActionContext | None = None,
    ) -> None:
        """删除指定权限。"""
        permission = self._get_permission_or_404(permission_id)
        if permission.is_system:
            raise DomainConflictError(
                code="SYSTEM_PERMISSION_DELETE_FORBIDDEN",
                message="System permissions cannot be deleted.",
            )
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=permission.id,
                    resource_name=permission.code,
                    response_status=status.HTTP_204_NO_CONTENT,
                ),
            )
        self.session.delete(permission)
        self.session.commit()
        logger.info("Permission deleted permission_id=%s.", permission_id)

    async def list_menus(self) -> list[MenuResponse]:
        """返回菜单平铺列表。"""
        menus = self.session.scalars(select(Menu).order_by(Menu.sort.asc(), Menu.id.asc())).all()
        return [self._to_menu_response(menu) for menu in menus]

    async def get_menu(self, menu_id: int) -> MenuResponse:
        """按菜单 ID 查询详情。"""
        return self._to_menu_response(self._get_menu_or_404(menu_id))

    async def list_menu_tree(self) -> list[MenuResponse]:
        """返回菜单树结构。"""
        menu_rows = [
            self._serialize_menu(menu)
            for menu in self.session.scalars(
                select(Menu).order_by(Menu.sort.asc(), Menu.id.asc())
            ).all()
        ]
        tree = build_menu_tree(menu_rows)
        return [MenuResponse.model_validate(node) for node in tree]

    async def create_menu(
        self,
        current_user,
        payload: MenuCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> MenuResponse:
        """创建新的菜单节点。"""
        if payload.parent_id is not None:
            self._get_menu_or_404(payload.parent_id)

        menu = Menu(
            parent_id=payload.parent_id,
            name=payload.name,
            path=payload.path,
            component=payload.component,
            icon=payload.icon,
            sort=payload.sort,
            visible=payload.visible,
            redirect=payload.redirect,
            meta=payload.meta,
            is_system=False,
        )
        self.session.add(menu)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=menu.id,
                    resource_name=menu.name,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self.session.commit()
        self.session.refresh(menu)
        logger.info("Menu created menu_id=%s path=%s.", menu.id, menu.path)
        return self._to_menu_response(menu)

    async def update_menu(
        self,
        current_user,
        menu_id: int,
        payload: MenuUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> MenuResponse:
        """更新指定菜单。"""
        menu = self._get_menu_or_404(menu_id)
        updates = payload.model_dump(exclude_unset=True)
        if "parent_id" in updates and updates["parent_id"] is not None:
            # 修改父级前先确认目标父菜单存在，避免写入孤儿节点。
            self._get_menu_or_404(int(updates["parent_id"]))
        for field_name, field_value in updates.items():
            setattr(menu, field_name, field_value)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=menu.id,
                    resource_name=menu.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(menu)
        logger.info("Menu updated menu_id=%s.", menu.id)
        return self._to_menu_response(menu)

    async def delete_menu(
        self,
        current_user,
        menu_id: int,
        audit_context: AuditActionContext | None = None,
    ) -> None:
        """删除指定菜单。"""
        menu = self._get_menu_or_404(menu_id)
        if menu.is_system:
            raise DomainConflictError(
                code="SYSTEM_MENU_DELETE_FORBIDDEN",
                message="System menus cannot be deleted.",
            )
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=menu.id,
                    resource_name=menu.name,
                    response_status=status.HTTP_204_NO_CONTENT,
                ),
            )
        self.session.delete(menu)
        self.session.commit()
        logger.info("Menu deleted menu_id=%s.", menu_id)

    def _get_role_or_404(self, role_id: int) -> Role:
        """读取角色，不存在则抛出 404。"""
        role = self.session.scalar(
            select(Role)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.menus),
            )
            .where(Role.id == role_id)
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )
        return role

    def _get_permission_or_404(self, permission_id: int) -> Permission:
        """读取权限，不存在则抛出 404。"""
        permission = self.session.scalar(
            select(Permission).where(Permission.id == permission_id)
        )
        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )
        return permission

    def _get_menu_or_404(self, menu_id: int) -> Menu:
        """读取菜单，不存在则抛出 404。"""
        menu = self.session.scalar(select(Menu).where(Menu.id == menu_id))
        if menu is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu not found.",
            )
        return menu

    def _get_permissions_or_404(self, permission_ids: list[int]) -> list[Permission]:
        """按 ID 列表读取权限，并确保全部存在。"""
        if not permission_ids:
            return []
        permissions = self.session.scalars(
            select(Permission)
            .where(Permission.id.in_(permission_ids))
            .order_by(Permission.id.asc())
        ).all()
        if len(permissions) != len(set(permission_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )
        return permissions

    def _get_menus_or_404(self, menu_ids: list[int]) -> list[Menu]:
        """按 ID 列表读取菜单，并确保全部存在。"""
        if not menu_ids:
            return []
        menus = self.session.scalars(
            select(Menu).where(Menu.id.in_(menu_ids)).order_by(Menu.id.asc())
        ).all()
        if len(menus) != len(set(menu_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu not found.",
            )
        return menus

    @staticmethod
    def _to_permission_response(permission: Permission) -> PermissionResponse:
        """将权限 ORM 对象转换为响应模型。"""
        return PermissionResponse(
            id=permission.id,
            name=permission.name,
            code=permission.code,
            resource=permission.resource,
            action=permission.action,
            description=permission.description,
            is_system=permission.is_system,
        )

    def _to_menu_response(self, menu: Menu) -> MenuResponse:
        """将菜单 ORM 对象转换为响应模型。"""
        return MenuResponse(
            id=menu.id,
            parent_id=menu.parent_id,
            name=menu.name,
            path=menu.path,
            component=menu.component,
            icon=menu.icon,
            sort=menu.sort,
            visible=menu.visible,
            redirect=menu.redirect,
            meta=menu.meta,
            is_system=menu.is_system,
            children=[],
        )

    def _to_role_response(self, role: Role) -> RoleResponse:
        """将角色 ORM 对象转换为响应模型。"""
        return RoleResponse(
            id=role.id,
            name=role.name,
            code=role.code,
            description=role.description,
            is_system=role.is_system,
            permissions=[
                self._to_permission_response(permission)
                for permission in sorted(role.permissions, key=lambda item: (item.code, item.id))
            ],
            menus=[
                self._to_menu_response(menu)
                for menu in sorted(role.menus, key=lambda item: (item.sort, item.id))
            ],
        )

    @staticmethod
    def _serialize_menu(menu: Menu) -> dict[str, object]:
        """将菜单对象转换为构造菜单树所需的中间结构。"""
        return {
            "id": menu.id,
            "parent_id": menu.parent_id,
            "name": menu.name,
            "path": menu.path,
            "component": menu.component,
            "icon": menu.icon,
            "sort": menu.sort,
            "visible": menu.visible,
            "redirect": menu.redirect,
            "meta": menu.meta,
            "is_system": menu.is_system,
        }
