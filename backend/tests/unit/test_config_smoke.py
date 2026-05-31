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


def test_settings_ignore_codereview_compatibility_keys() -> None:
    settings = Settings(
        gitlab_url="https://gitlab.example.com",
        gitlab_access_token="gitlab-token",
        github_url="https://github.com",
        github_api_url="https://api.github.com",
        github_access_token="github-token",
        llm_provider="openai",
        openai_api_key="openai-key",
        openai_api_base_url="https://example.com/v1",
        openai_api_model="gpt-4o-mini",
        supported_extensions=".py,.ts",
        review_max_tokens="10000",
        review_style="professional",
        push_review_enabled="1",
        merge_review_only_protected_branches_enabled="0",
    )

    assert settings.app_name == "AI Code Reviewer"


def test_settings_exposes_dev_worker_flags(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        Settings,
        "model_config",
        {**Settings.model_config, "env_file": env_file},
    )

    settings = Settings()

    assert settings.dev_autostart_worker is True
