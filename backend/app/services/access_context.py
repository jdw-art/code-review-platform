from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Menu, Permission, Role, User
from app.db.session import get_db
from app.schemas.me import (
    AccessContextResponse,
    CurrentUserProfileResponse,
    CurrentUserRoleSummary,
    CurrentUserSummary,
)


def build_menu_tree(menu_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将菜单平铺列表组装为树形结构。"""
    nodes_by_id: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for menu_row in menu_rows:
        node = {**menu_row, "children": []}
        nodes_by_id[int(node["id"])] = node

    for node in nodes_by_id.values():
        parent_id = node.get("parent_id")
        if parent_id is None:
            roots.append(node)
            continue

        parent = nodes_by_id.get(int(parent_id))
        if parent is None:
            # 菜单树必须保持父节点完整，否则前端导航树会出现不可恢复的不一致。
            raise ValueError(
                f"Menu node {node['id']} references missing parent {parent_id}."
            )

        parent["children"].append(node)

    return roots


class AccessContextService:
    """聚合当前用户的资料、角色、权限与菜单上下文。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def get_permission_codes(self, user_id: int) -> list[str]:
        """获取指定用户的权限编码列表。"""
        user = self._get_user_with_access_context(user_id)
        if user.is_superuser:
            return self._get_all_permission_codes()
        return self._get_permission_codes_from_roles(user.roles)

    async def get_access_context(self, current_user: User) -> AccessContextResponse:
        """构造前端初始化所需的访问上下文。"""
        user = self._get_user_with_access_context(current_user.id)
        if user.is_superuser:
            # 超级管理员直接看到系统中的全部权限与菜单。
            permission_codes = self._get_all_permission_codes()
            menu_rows = self._serialize_all_menus()
        else:
            permission_codes = self._get_permission_codes_from_roles(user.roles)
            menu_rows = self._serialize_menus(user.roles)

        return AccessContextResponse(
            user=CurrentUserSummary(
                id=user.id,
                username=user.username,
                nickname=user.nickname,
                email=user.email,
                phone=user.phone,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
            ),
            roles=[
                CurrentUserRoleSummary(id=role.id, name=role.name, code=role.code)
                for role in sorted(user.roles, key=lambda role: (role.name, role.id))
            ],
            permissions=permission_codes,
            menus=build_menu_tree(menu_rows),
            must_change_password=user.must_change_password,
        )

    async def get_profile(self, current_user: User) -> CurrentUserProfileResponse:
        """返回当前用户资料摘要。"""
        user = self._get_user_with_access_context(current_user.id)
        return CurrentUserProfileResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            phone=user.phone,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            must_change_password=user.must_change_password,
            roles=[
                CurrentUserRoleSummary(id=role.id, name=role.name, code=role.code)
                for role in sorted(user.roles, key=lambda role: (role.name, role.id))
            ],
        )

    def _get_user_with_access_context(self, user_id: int) -> User:
        """一次性加载用户、角色、权限和菜单，避免后续重复查询。"""
        statement = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.menus),
            )
            .where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )
        user = self.session.scalar(statement)
        if user is None:
            raise ValueError(f"Active user {user_id} was not found.")
        return user

    @staticmethod
    def _serialize_menus(roles: list[Role]) -> list[dict[str, Any]]:
        """从角色集合中提取菜单并按 ID 去重。"""
        menu_rows_by_id: dict[int, dict[str, Any]] = {}

        for role in roles:
            for menu in role.menus:
                menu_rows_by_id[menu.id] = {
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
                }

        return sorted(
            menu_rows_by_id.values(),
            key=lambda menu_row: (int(menu_row["sort"]), int(menu_row["id"])),
        )

    def _serialize_all_menus(self) -> list[dict[str, Any]]:
        """序列化系统中的全部菜单。"""
        menus = self.session.scalars(
            select(Menu).order_by(Menu.sort.asc(), Menu.id.asc())
        ).all()
        return [self._serialize_menu(menu) for menu in menus]

    @staticmethod
    def _get_permission_codes_from_roles(roles: list[Role]) -> list[str]:
        """从角色集合中汇总唯一权限编码。"""
        return sorted(
            {
                permission.code
                for role in roles
                for permission in role.permissions
            }
        )

    def _get_all_permission_codes(self) -> list[str]:
        """读取系统中的全部权限编码。"""
        return sorted(
            self.session.scalars(
                select(Permission.code).order_by(Permission.code.asc())
            ).all()
        )

    @staticmethod
    def _serialize_menu(menu: Menu) -> dict[str, Any]:
        """将 ORM 菜单对象转换为可序列化字典。"""
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
        }
