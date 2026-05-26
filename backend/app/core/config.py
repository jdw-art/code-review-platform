from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="AI_CODE_REVIEWER_",
    )

    app_name: str = "AI Code Reviewer"
    api_prefix: str = "/api/v1"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_code_reviewer"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    jwt_secret_key: str = "change-me-in-env"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "jdw112233"

    def uses_insecure_auth_defaults(self) -> bool:
        return (
            self.jwt_secret_key == "change-me-in-env"
            or self.bootstrap_admin_password == "jdw112233"
        )
