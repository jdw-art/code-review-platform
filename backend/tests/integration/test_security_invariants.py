from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import Menu, Permission, Role, User


def _flatten_menu_paths(menu_nodes: list[dict[str, object]]) -> set[str]:
    paths: set[str] = set()
    stack = list(menu_nodes)
    while stack:
        node = stack.pop()
        path = node.get("path")
        if isinstance(path, str):
            paths.add(path)
        children = node.get("children")
        if isinstance(children, list):
            stack.extend(children)
    return paths


def test_must_change_password_blocks_management_api(authenticated_default_password_client):
    response = authenticated_default_password_client.get("/api/v1/users")

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "PASSWORD_CHANGE_REQUIRED"
    assert body["message"] == "Password change required."
    assert body["request_id"]


def test_must_change_password_allows_safe_profile_endpoint(
    authenticated_default_password_client,
):
    response = authenticated_default_password_client.get("/api/v1/me/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin"
    assert body["must_change_password"] is True


def test_cannot_disable_own_account(authenticated_superuser_client, db_session):
    current_user = db_session.scalar(select(User).where(User.username == "root-admin"))
    assert current_user is not None

    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{current_user.id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "SELF_DISABLE_FORBIDDEN"
    assert body["message"] == "You cannot disable your own account."


def test_cannot_remove_own_superuser_status(authenticated_superuser_client, db_session):
    current_user = db_session.scalar(select(User).where(User.username == "root-admin"))
    assert current_user is not None

    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{current_user.id}",
        json={"is_superuser": False},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "SELF_DEMOTE_FORBIDDEN"
    assert body["message"] == "You cannot remove your own superuser status."


def test_cannot_disable_last_superuser(authenticated_superuser_client, db_session):
    settings = Settings()
    bootstrap_admin = db_session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )
    current_user = db_session.scalar(select(User).where(User.username == "root-admin"))
    assert bootstrap_admin is not None
    assert current_user is not None

    bootstrap_admin.is_superuser = False
    db_session.commit()

    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{current_user.id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "LAST_SUPERUSER_DISABLE_FORBIDDEN"
    assert body["message"] == "The last superuser cannot be disabled."


def test_cannot_remove_last_superuser_status(authenticated_superuser_client, db_session):
    settings = Settings()
    bootstrap_admin = db_session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )
    current_user = db_session.scalar(select(User).where(User.username == "root-admin"))
    assert bootstrap_admin is not None
    assert current_user is not None

    bootstrap_admin.is_superuser = False
    db_session.commit()

    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{current_user.id}",
        json={"is_superuser": False},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "LAST_SUPERUSER_DEMOTE_FORBIDDEN"
    assert body["message"] == "The last superuser status cannot be removed."


@pytest.mark.parametrize(
    ("path", "factory", "expected_code"),
    [
        (
            "/api/v1/roles/{id}",
            lambda: Role(
                name="System Role",
                code="system-role",
                description="Managed by system",
                is_system=True,
            ),
            "SYSTEM_ROLE_DELETE_FORBIDDEN",
        ),
        (
            "/api/v1/permissions/{id}",
            lambda: Permission(
                name="System Permission",
                code="system:manage",
                resource="system",
                action="manage",
                is_system=True,
            ),
            "SYSTEM_PERMISSION_DELETE_FORBIDDEN",
        ),
        (
            "/api/v1/menus/{id}",
            lambda: Menu(
                name="System Menu",
                path="/system",
                sort=10,
                visible=True,
                is_system=True,
            ),
            "SYSTEM_MENU_DELETE_FORBIDDEN",
        ),
    ],
)
def test_cannot_delete_system_managed_resources(
    authenticated_superuser_client,
    db_session,
    path,
    factory,
    expected_code,
):
    resource = factory()
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)

    response = authenticated_superuser_client.delete(path.format(id=resource.id))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == expected_code
    assert body["request_id"]


def test_access_context_exposes_phase2_permissions_and_menus(
    authenticated_superuser_client,
):
    response = authenticated_superuser_client.get("/api/v1/me/access-context")

    assert response.status_code == 200
    body = response.json()
    permissions = set(body["permissions"])
    menu_paths = _flatten_menu_paths(body["menus"])

    assert {
        "dashboard:read",
        "project:read",
        "project:create",
        "project:update",
        "project:status",
        "project_template:read",
        "project_template:create",
        "project_template:update",
        "project_template:status",
        "llm_model:read",
        "llm_model:create",
        "llm_model:update",
        "llm_model:status",
        "notification_bot:read",
        "notification_bot:create",
        "notification_bot:update",
        "notification_bot:status",
        "review_record:read",
        "review_record:raw",
        "review_record:import",
        "member_analytics:read",
        "audit_log:read",
    }.issubset(permissions)
    assert {
        "/projects",
        "/project-templates",
        "/dashboard",
        "/models",
        "/notification-bots",
        "/review-records",
        "/member-analytics",
        "/audit-logs",
    }.issubset(menu_paths)
