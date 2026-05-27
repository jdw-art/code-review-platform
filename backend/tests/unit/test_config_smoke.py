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
