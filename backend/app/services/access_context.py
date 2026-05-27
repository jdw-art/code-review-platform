from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Role, User
from app.db.session import get_db
from app.schemas.me import AccessContextResponse, CurrentUserRoleSummary, CurrentUserSummary


def build_menu_tree(menu_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            roots.append(node)
            continue

        parent["children"].append(node)

    return roots


class AccessContextService:
    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def get_permission_codes(self, user_id: int) -> list[str]:
        user = self._get_user_with_access_context(user_id)
        return self._get_permission_codes_from_roles(user.roles)

    async def get_access_context(self, current_user: User) -> AccessContextResponse:
        user = self._get_user_with_access_context(current_user.id)
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

    def _get_user_with_access_context(self, user_id: int) -> User:
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

    @staticmethod
    def _get_permission_codes_from_roles(roles: list[Role]) -> list[str]:
        return sorted(
            {
                permission.code
                for role in roles
                for permission in role.permissions
            }
        )
