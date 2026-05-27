from __future__ import annotations

import pytest

from app.db.models import Permission, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def limited_permission_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    role = Role(name="Reviewer", code="reviewer", permissions=[permission])
    user = User(
        username="permission-limited-user",
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


def test_admin_can_create_list_update_and_delete_permissions(
    authenticated_superuser_client,
):
    create_response = authenticated_superuser_client.post(
        "/api/v1/permissions",
        json={
            "name": "Create User",
            "code": "user:create",
            "resource": "user",
            "action": "create",
            "description": "Create users",
        },
    )

    assert create_response.status_code == 201
    permission = create_response.json()
    assert permission["code"] == "user:create"

    list_response = authenticated_superuser_client.get("/api/v1/permissions")
    assert list_response.status_code == 200
    assert any(item["id"] == permission["id"] for item in list_response.json())

    update_response = authenticated_superuser_client.patch(
        f"/api/v1/permissions/{permission['id']}",
        json={"description": "Create platform users"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Create platform users"

    delete_response = authenticated_superuser_client.delete(
        f"/api/v1/permissions/{permission['id']}"
    )
    assert delete_response.status_code == 204


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/permissions", None),
        (
            "post",
            "/api/v1/permissions",
            {
                "name": "Nope",
                "code": "nope:create",
                "resource": "nope",
                "action": "create",
            },
        ),
        ("patch", "/api/v1/permissions/999999", {"description": "No Access"}),
        ("delete", "/api/v1/permissions/999999", None),
    ],
)
def test_permission_management_endpoints_require_permissions(
    limited_permission_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload
    response = getattr(limited_permission_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
