import pytest

from app.db.models import Menu, Permission, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def normal_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    root_menu = Menu(
        name="Workspace",
        path="/workspace",
        icon="dashboard",
        sort=10,
    )
    child_menu = Menu(
        name="Reviews",
        path="/workspace/reviews",
        parent=root_menu,
        sort=20,
    )
    role = Role(
        name="Reviewer",
        code="reviewer",
        permissions=[permission],
        menus=[root_menu, child_menu],
    )
    user = User(
        username="reviewer",
        password_hash=hash_password("reviewer-password"),
        nickname="Review Captain",
        email="reviewer@example.com",
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


def test_me_access_context_returns_normal_user_permissions_and_nested_menus(
    normal_user_client,
):
    response = normal_user_client.get("/api/v1/me/access-context")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "reviewer"
    assert body["user"]["nickname"] == "Review Captain"
    assert body["must_change_password"] is False
    assert len(body["roles"]) == 1
    assert body["roles"][0]["name"] == "Reviewer"
    assert body["roles"][0]["code"] == "reviewer"
    assert body["permissions"] == ["reviews.read"]
    assert body["menus"][0]["name"] == "Workspace"
    assert body["menus"][0]["path"] == "/workspace"
    assert body["menus"][0]["children"][0]["name"] == "Reviews"


def test_me_access_context_rejects_unauthenticated_requests(client):
    response = client.get("/api/v1/me/access-context")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_me_access_context_rejects_invalid_subject_claim(client, monkeypatch):
    monkeypatch.setattr(
        "app.security.deps.decode_token",
        lambda token, expected_token_type: {
            "sub": "not-an-integer",
            "token_type": expected_token_type,
        },
    )
    client.headers.update({"Authorization": "Bearer malformed-sub"})

    response = client.get("/api/v1/me/access-context")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token."
