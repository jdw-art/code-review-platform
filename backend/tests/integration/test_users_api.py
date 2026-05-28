from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Permission, RefreshSession, Role, User
from app.security.passwords import hash_password
from app.security.tokens import decode_token, issue_access_token


@pytest.fixture
def managed_user(db_session) -> User:
    user = User(
        username="managed-user",
        password_hash=hash_password("managed-password"),
        nickname="Managed User",
        email="managed@example.com",
        phone="15500000000",
        is_active=True,
        is_superuser=False,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def limited_user_client(client, db_session):
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
        username="limited-user",
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


@pytest.fixture
def authenticated_superuser_client(client, db_session):
    user = User(
        username="root-admin",
        password_hash=hash_password("root-admin-password"),
        nickname="Root Admin",
        is_active=True,
        is_superuser=True,
        must_change_password=False,
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


@pytest.fixture
def user_delete_operator_client(client, db_session):
    permission = db_session.scalar(select(Permission).where(Permission.code == "user:delete"))
    assert permission is not None
    role = Role(
        name="User Operator",
        code="user-operator",
        permissions=[permission],
    )
    user = User(
        username="user-delete-operator",
        password_hash=hash_password("operator-password"),
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


def test_admin_can_create_user(authenticated_superuser_client, db_session):
    response = authenticated_superuser_client.post(
        "/api/v1/users",
        json={
            "username": "alice",
            "password": "alice123456",
            "nickname": "Alice",
            "email": "alice@example.com",
            "phone": "15500000001",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["username"] == "alice"
    assert body["nickname"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert body["phone"] == "15500000001"
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert body["must_change_password"] is False
    assert body["roles"] == []

    user = db_session.scalar(select(User).where(User.username == "alice"))
    assert user is not None
    assert user.password_hash != "alice123456"


def test_admin_can_list_users(authenticated_superuser_client, managed_user):
    response = authenticated_superuser_client.get("/api/v1/users")

    assert response.status_code == 200
    body = response.json()
    assert any(user["id"] == managed_user.id for user in body)
    assert any(user["username"] == "admin" for user in body)
    assert all(isinstance(user["id"], int) for user in body)


def test_admin_can_get_user_detail(authenticated_superuser_client, managed_user):
    response = authenticated_superuser_client.get(f"/api/v1/users/{managed_user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == managed_user.id
    assert body["username"] == "managed-user"
    assert body["nickname"] == "Managed User"
    assert body["email"] == "managed@example.com"
    assert body["phone"] == "15500000000"
    assert body["roles"] == []


def test_admin_can_update_user_profile_fields(
    authenticated_superuser_client,
    managed_user,
    db_session,
):
    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{managed_user.id}",
        json={
            "nickname": "Updated User",
            "email": "updated@example.com",
            "phone": "15500009999",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nickname"] == "Updated User"
    assert body["email"] == "updated@example.com"
    assert body["phone"] == "15500009999"

    db_session.refresh(managed_user)
    assert managed_user.nickname == "Updated User"
    assert managed_user.email == "updated@example.com"
    assert managed_user.phone == "15500009999"


def test_admin_can_toggle_user_active_status(
    authenticated_superuser_client,
    managed_user,
    db_session,
):
    response = authenticated_superuser_client.patch(
        f"/api/v1/users/{managed_user.id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False

    db_session.refresh(managed_user)
    assert managed_user.is_active is False


def test_admin_can_reset_password_and_revoke_all_refresh_sessions(
    authenticated_superuser_client,
    managed_user,
    refresh_session_store,
    test_session_factory,
):
    first_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "managed-password"},
    )
    second_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "managed-password"},
    )
    refresh_tokens = [
        str(first_login_response.json()["refresh_token"]),
        str(second_login_response.json()["refresh_token"]),
    ]
    refresh_claims = [
        decode_token(refresh_token, expected_token_type="refresh")
        for refresh_token in refresh_tokens
    ]

    assert first_login_response.status_code == 200
    assert second_login_response.status_code == 200
    assert refresh_session_store.user_index[managed_user.id] == {
        claims["jti"] for claims in refresh_claims
    }

    response = authenticated_superuser_client.post(
        f"/api/v1/users/{managed_user.id}/reset-password",
        json={"new_password": "new-password-123"},
    )

    assert response.status_code == 204
    assert managed_user.id not in refresh_session_store.user_index

    for refresh_token in refresh_tokens:
        replay_response = authenticated_superuser_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert replay_response.status_code == 401

    old_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "managed-password"},
    )
    assert old_login_response.status_code == 401

    new_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "new-password-123"},
    )
    assert new_login_response.status_code == 200
    assert new_login_response.json()["must_change_password"] is True

    with test_session_factory() as session:
        stored_user = session.scalar(select(User).where(User.id == managed_user.id))
        stored_sessions = session.scalars(
            select(RefreshSession).where(
                RefreshSession.jti.in_([claims["jti"] for claims in refresh_claims])
            )
        ).all()

        assert stored_user is not None
        assert stored_user.must_change_password is True
        assert len(stored_sessions) == 2
        assert all(refresh_session.revoked_at is not None for refresh_session in stored_sessions)


def test_admin_can_assign_roles(
    authenticated_superuser_client,
    managed_user,
    created_role,
    db_session,
):
    response = authenticated_superuser_client.put(
        f"/api/v1/users/{managed_user.id}/roles",
        json={"role_ids": [created_role["id"]]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["roles"] == [created_role]

    db_session.refresh(managed_user)
    assert [role.id for role in managed_user.roles] == [created_role["id"]]


def test_admin_can_delete_user_and_revoke_refresh_sessions(
    authenticated_superuser_client,
    managed_user,
    refresh_session_store,
    test_session_factory,
    db_session,
):
    first_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "managed-password"},
    )
    second_login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "managed-user", "password": "managed-password"},
    )
    refresh_tokens = [
        str(first_login_response.json()["refresh_token"]),
        str(second_login_response.json()["refresh_token"]),
    ]
    refresh_claims = [
        decode_token(refresh_token, expected_token_type="refresh")
        for refresh_token in refresh_tokens
    ]

    assert first_login_response.status_code == 200
    assert second_login_response.status_code == 200
    assert refresh_session_store.user_index[managed_user.id] == {
        claims["jti"] for claims in refresh_claims
    }

    response = authenticated_superuser_client.delete(f"/api/v1/users/{managed_user.id}")

    assert response.status_code == 204
    assert managed_user.id not in refresh_session_store.user_index
    assert db_session.scalar(select(User).where(User.id == managed_user.id)) is None

    for refresh_token in refresh_tokens:
        replay_response = authenticated_superuser_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert replay_response.status_code == 401

    with test_session_factory() as session:
        stored_sessions = session.scalars(
            select(RefreshSession).where(
                RefreshSession.jti.in_([claims["jti"] for claims in refresh_claims])
            )
        ).all()
        assert stored_sessions == []


def test_admin_cannot_delete_self(authenticated_superuser_client, db_session):
    current_user = db_session.scalar(select(User).where(User.username == "root-admin"))
    assert current_user is not None

    response = authenticated_superuser_client.delete(f"/api/v1/users/{current_user.id}")

    assert response.status_code == 409
    assert response.json()["code"] == "SELF_DELETE_FORBIDDEN"
    assert response.json()["message"] == "You cannot delete your own account."


def test_operator_cannot_delete_last_active_superuser(
    user_delete_operator_client,
    bootstrap_admin,
    db_session,
):
    bootstrap_admin.is_active = False
    target_superuser = User(
        username="sole-superuser",
        password_hash=hash_password("sole-superuser-password"),
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    db_session.add(target_superuser)
    db_session.commit()
    db_session.refresh(target_superuser)

    response = user_delete_operator_client.delete(f"/api/v1/users/{target_superuser.id}")

    assert response.status_code == 409
    assert response.json()["code"] == "LAST_SUPERUSER_DELETE_FORBIDDEN"
    assert response.json()["message"] == "The last superuser cannot be deleted."
    assert db_session.scalar(select(User).where(User.id == target_superuser.id)) is not None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/users", {"username": "bob", "password": "bob123456"}),
        ("get", "/api/v1/users", None),
        ("get", "/api/v1/users/999999", None),
        ("patch", "/api/v1/users/999999", {"nickname": "No Access"}),
        ("patch", "/api/v1/users/999999/status", {"is_active": False}),
        ("post", "/api/v1/users/999999/reset-password", {"new_password": "new-password-123"}),
        ("put", "/api/v1/users/999999/roles", {"role_ids": []}),
        ("delete", "/api/v1/users/999999", None),
    ],
)
def test_user_management_endpoints_require_permissions(
    limited_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload
    response = getattr(limited_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
