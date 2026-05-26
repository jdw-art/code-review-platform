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
