from sqlalchemy import select

from app.db.models import RefreshSession, User
from app.security.tokens import decode_token


def test_login_returns_token_pair(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["must_change_password"] is True


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert response.json()["message"] == "Invalid username or password."


def test_refresh_rotates_refresh_token_and_revokes_previous_session(
    authenticated_default_password_client,
    default_password_token_pair,
    refresh_session_store,
    test_session_factory,
):
    refresh_token = default_password_token_pair["refresh_token"]
    response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    replacement_refresh_token = response.json()["refresh_token"]
    assert replacement_refresh_token != refresh_token

    previous_claims = decode_token(str(refresh_token), expected_token_type="refresh")
    replacement_claims = decode_token(
        replacement_refresh_token,
        expected_token_type="refresh",
    )
    assert previous_claims["jti"] != replacement_claims["jti"]
    assert previous_claims["jti"] not in refresh_session_store.sessions
    assert (
        refresh_session_store.sessions[replacement_claims["jti"]]
        == int(replacement_claims["sub"])
    )

    replay_response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_response.status_code == 401

    with test_session_factory() as session:
        previous_session = session.scalar(
            select(RefreshSession).where(
                RefreshSession.jti == previous_claims["jti"]
            )
        )
        replacement_session = session.scalar(
            select(RefreshSession).where(
                RefreshSession.jti == replacement_claims["jti"]
            )
        )

        assert previous_session is not None
        assert previous_session.revoked_at is not None
        assert previous_session.replaced_by_jti == replacement_claims["jti"]
        assert replacement_session is not None
        assert replacement_session.revoked_at is None


def test_logout_revokes_refresh_session(
    authenticated_default_password_client,
    refresh_token,
    refresh_session_store,
    test_session_factory,
):
    claims = decode_token(refresh_token, expected_token_type="refresh")
    response = authenticated_default_password_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 204
    assert claims["jti"] not in refresh_session_store.sessions

    replay_response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_response.status_code == 401

    with test_session_factory() as session:
        refresh_session = session.scalar(
            select(RefreshSession).where(RefreshSession.jti == claims["jti"])
        )

        assert refresh_session is not None
        assert refresh_session.revoked_at is not None


def test_logout_all_revokes_refresh_sessions(
    authenticated_default_password_client,
    default_password_token_pair,
    refresh_session_store,
    test_session_factory,
):
    second_login_response = authenticated_default_password_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    second_refresh_token = second_login_response.json()["refresh_token"]
    refresh_tokens = [
        str(default_password_token_pair["refresh_token"]),
        second_refresh_token,
    ]
    refresh_claims = [
        decode_token(refresh_token, expected_token_type="refresh")
        for refresh_token in refresh_tokens
    ]

    response = authenticated_default_password_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 204
    assert refresh_session_store.sessions == {}
    assert refresh_session_store.user_index == {}

    for refresh_token in refresh_tokens:
        replay_response = authenticated_default_password_client.post(
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

        assert len(stored_sessions) == 2
        assert all(refresh_session.revoked_at is not None for refresh_session in stored_sessions)


def test_change_password_updates_credentials_and_revokes_existing_sessions(
    authenticated_default_password_client,
    refresh_token,
    refresh_session_store,
    test_session_factory,
):
    refresh_claims = decode_token(refresh_token, expected_token_type="refresh")
    response = authenticated_default_password_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "jdw112233",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == 204
    assert refresh_session_store.sessions == {}
    assert refresh_session_store.user_index == {}

    old_login_response = authenticated_default_password_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    assert old_login_response.status_code == 401

    new_login_response = authenticated_default_password_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "new-password-123"},
    )
    assert new_login_response.status_code == 200
    assert new_login_response.json()["must_change_password"] is False

    replay_response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_response.status_code == 401

    with test_session_factory() as session:
        user = session.scalar(select(User).where(User.username == "admin"))
        refresh_session = session.scalar(
            select(RefreshSession).where(RefreshSession.jti == refresh_claims["jti"])
        )

        assert user is not None
        assert user.must_change_password is False
        assert refresh_session is not None
        assert refresh_session.revoked_at is not None
