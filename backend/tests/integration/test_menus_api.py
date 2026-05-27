from __future__ import annotations

import pytest

from app.db.models import Permission, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def limited_menu_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    role = Role(name="Reviewer", code="reviewer", permissions=[permission])
    user = User(
        username="menu-limited-user",
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


def test_admin_can_create_list_update_tree_and_delete_menus(
    authenticated_superuser_client,
):
    create_root_response = authenticated_superuser_client.post(
        "/api/v1/menus",
        json={
            "name": "System",
            "path": "/system",
            "sort": 10,
            "visible": True,
            "icon": "settings",
        },
    )
    assert create_root_response.status_code == 201
    root_menu = create_root_response.json()

    create_child_response = authenticated_superuser_client.post(
        "/api/v1/menus",
        json={
            "name": "Users",
            "path": "/system/users",
            "parent_id": root_menu["id"],
            "sort": 20,
            "visible": True,
        },
    )
    assert create_child_response.status_code == 201
    child_menu = create_child_response.json()

    list_response = authenticated_superuser_client.get("/api/v1/menus")
    assert list_response.status_code == 200
    assert any(item["id"] == root_menu["id"] for item in list_response.json())
    assert any(item["id"] == child_menu["id"] for item in list_response.json())

    update_response = authenticated_superuser_client.patch(
        f"/api/v1/menus/{child_menu['id']}",
        json={"name": "Members", "path": "/system/members"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Members"

    tree_response = authenticated_superuser_client.get("/api/v1/menus/tree")
    assert tree_response.status_code == 200
    tree_body = tree_response.json()
    assert tree_body[0]["id"] == root_menu["id"]
    assert tree_body[0]["children"][0]["id"] == child_menu["id"]

    delete_response = authenticated_superuser_client.delete(f"/api/v1/menus/{child_menu['id']}")
    assert delete_response.status_code == 204


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/menus", None),
        ("get", "/api/v1/menus/tree", None),
        ("post", "/api/v1/menus", {"name": "Nope", "path": "/nope", "sort": 1, "visible": True}),
        ("patch", "/api/v1/menus/999999", {"name": "No Access"}),
        ("delete", "/api/v1/menus/999999", None),
    ],
)
def test_menu_management_endpoints_require_permissions(
    limited_menu_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload
    response = getattr(limited_menu_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
