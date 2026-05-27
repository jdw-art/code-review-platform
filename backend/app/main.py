from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.services.bootstrap import run_bootstrap


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.uses_insecure_auth_defaults():
        logging.getLogger(__name__).warning(
            "Backend is running with insecure bootstrap auth defaults. "
            "Set AI_CODE_REVIEWER_JWT_SECRET_KEY and "
            "AI_CODE_REVIEWER_BOOTSTRAP_ADMIN_PASSWORD before any non-local use."
        )
    await run_bootstrap()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_prefix)
