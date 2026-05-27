def test_login_returns_token_pair(client, bootstrap_admin):
    del bootstrap_admin
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["must_change_password"] is True


def test_refresh_rotates_refresh_token(
    authenticated_default_password_client,
    refresh_token,
):
    response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != refresh_token


def test_logout_all_revokes_refresh_sessions(authenticated_default_password_client):
    response = authenticated_default_password_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 204
