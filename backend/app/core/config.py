from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SECRET_ENCRYPTION_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="AI_CODE_REVIEWER_",
        extra="ignore",
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
    dev_autostart_worker: bool = False
    use_backend_reviewer: bool = False
    review_queue_name: Annotated[str, Field(min_length=1)] = "review:jobs"
    review_lock_prefix: Annotated[str, Field(min_length=1)] = "review:lock"
    review_max_retries: Annotated[int, Field(ge=0)] = 3
    review_lock_ttl_seconds: Annotated[int, Field(gt=0)] = 1800
    report_crontab_expression: str = "0 18 * * 1-5"
    jwt_secret_key: str = "change-me-in-env"
    secret_encryption_key: str = DEFAULT_SECRET_ENCRYPTION_KEY
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "jdw112233"

    def uses_insecure_auth_defaults(self) -> bool:
        return (
            self.jwt_secret_key == "change-me-in-env"
            or self.secret_encryption_key == DEFAULT_SECRET_ENCRYPTION_KEY
            or self.bootstrap_admin_password == "jdw112233"
        )
