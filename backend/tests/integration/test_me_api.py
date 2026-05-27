import pytest


@pytest.fixture
def authenticated_client(authenticated_default_password_client):
    return authenticated_default_password_client


def test_me_access_context_returns_permissions_and_menus(authenticated_client):
    response = authenticated_client.get("/api/v1/me/access-context")

    assert response.status_code == 200
    body = response.json()
    assert "permissions" in body
    assert "menus" in body
