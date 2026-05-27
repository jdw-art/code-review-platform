from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Menu, Permission, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def limited_role_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    role = Role(
        name="Reviewer",
        code="reviewer",
        permissions=[permission],
    )
    user = User(
        username="role-limited-user",
        password_hash=hash_password("limited-password"),
        is_active=True,
        is_superuser=False,
        must_change_password=False,
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    access_token = issue_access_token(
        user_id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
    )
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


def test_admin_can_create_list_and_get_roles(authenticated_superuser_client):
    create_response = authenticated_superuser_client.post(
        "/api/v1/roles",
        json={
            "name": "Maintainer",
            "code": "maintainer",
            "description": "Maintains reviewer configs",
        },
    )

    assert create_response.status_code == 201
    created_role = create_response.json()
    assert created_role["name"] == "Maintainer"
    assert created_role["code"] == "maintainer"
    assert created_role["permissions"] == []
    assert created_role["menus"] == []

    list_response = authenticated_superuser_client.get("/api/v1/roles")
    assert list_response.status_code == 200
    assert any(role["id"] == created_role["id"] for role in list_response.json())

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/roles/{created_role['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["code"] == "maintainer"


def test_admin_can_update_role_and_assign_permissions_and_menus(
    authenticated_superuser_client,
    db_session,
):
    role = Role(name="Reviewer", code="reviewer", description="Reviews code")
    permission = Permission(
        name="User Create",
        code="user:create",
        resource="user",
        action="create",
    )
    root_menu = Menu(
        name="System",
        path="/system",
        sort=10,
        visible=True,
    )
    child_menu = Menu(
        name="Users",
        path="/system/users",
        parent=root_menu,
        sort=20,
        visible=True,
    )
    db_session.add_all([role, permission, root_menu, child_menu])
    db_session.commit()
    db_session.refresh(role)
    db_session.refresh(permission)
    db_session.refresh(root_menu)
    db_session.refresh(child_menu)

    update_response = authenticated_superuser_client.patch(
        f"/api/v1/roles/{role.id}",
        json={"name": "Senior Reviewer", "description": "Updated description"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Senior Reviewer"

    permission_response = authenticated_superuser_client.put(
        f"/api/v1/roles/{role.id}/permissions",
        json={"permission_ids": [permission.id]},
    )
    assert permission_response.status_code == 200
    assigned_permission = permission_response.json()["permissions"][0]
    assert assigned_permission["id"] == permission.id
    assert assigned_permission["name"] == "User Create"
    assert assigned_permission["code"] == "user:create"
    assert assigned_permission["resource"] == "user"
    assert assigned_permission["action"] == "create"

    menu_response = authenticated_superuser_client.put(
        f"/api/v1/roles/{role.id}/menus",
        json={"menu_ids": [root_menu.id, child_menu.id]},
    )
    assert menu_response.status_code == 200
    assert [menu["id"] for menu in menu_response.json()["menus"]] == [
        root_menu.id,
        child_menu.id,
    ]


def test_admin_can_delete_role(authenticated_superuser_client, db_session):
    role = Role(name="Observer", code="observer", description="Read only")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    response = authenticated_superuser_client.delete(f"/api/v1/roles/{role.id}")

    assert response.status_code == 204
    assert db_session.scalar(select(Role).where(Role.id == role.id)) is None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/roles", None),
        ("get", "/api/v1/roles/999999", None),
        ("post", "/api/v1/roles", {"name": "Nope", "code": "nope"}),
        ("patch", "/api/v1/roles/999999", {"name": "No Access"}),
        ("delete", "/api/v1/roles/999999", None),
        ("put", "/api/v1/roles/999999/permissions", {"permission_ids": []}),
        ("put", "/api/v1/roles/999999/menus", {"menu_ids": []}),
    ],
)
def test_role_management_endpoints_require_permissions(
    limited_role_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload
    response = getattr(limited_role_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
