from app.core.crypto import SecretCipher
from app.core.config import Settings


def test_settings_use_project_defaults():
    settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="ai_code_reviewer",
        postgres_user="postgres",
        postgres_password="postgres",
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
    )

    assert settings.postgres_db == "ai_code_reviewer"
    assert settings.redis_port == 6379
    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 7


def test_settings_expose_secret_encryption_key() -> None:
    settings = Settings()

    assert settings.secret_encryption_key


def test_settings_default_secret_encryption_key_supports_round_trip() -> None:
    settings = Settings()
    cipher = SecretCipher(settings.secret_encryption_key)
    encrypted = cipher.encrypt_text("top-secret")

    assert encrypted != "top-secret"
    assert cipher.decrypt_text(encrypted) == "top-secret"


def test_settings_flag_default_secret_encryption_key_as_insecure() -> None:
    settings = Settings(
        jwt_secret_key="custom-jwt-secret",
        bootstrap_admin_password="custom-bootstrap-password",
    )

    assert settings.uses_insecure_auth_defaults() is True
