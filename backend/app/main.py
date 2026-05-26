import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings
from app.core.logging import configure_logging


settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def setup_logging() -> None:
    configure_logging()
    if settings.uses_insecure_auth_defaults():
        logging.getLogger(__name__).warning(
            "Backend is running with insecure bootstrap auth defaults. "
            "Set AI_CODE_REVIEWER_JWT_SECRET_KEY and "
            "AI_CODE_REVIEWER_BOOTSTRAP_ADMIN_PASSWORD before any non-local use."
        )
