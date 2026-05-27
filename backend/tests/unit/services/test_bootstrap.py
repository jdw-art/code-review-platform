from app.services.bootstrap import build_bootstrap_admin_payload


def test_bootstrap_admin_requires_password_change() -> None:
    payload = build_bootstrap_admin_payload()

    assert payload["username"] == "admin"
    assert payload["is_superuser"] is True
    assert payload["must_change_password"] is True
