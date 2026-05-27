import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.schemas.common import DomainError, ErrorResponse
from app.services.bootstrap import run_bootstrap


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.uses_insecure_auth_defaults():
        logging.getLogger(__name__).warning(
            "Backend is running with insecure bootstrap auth defaults. "
            "Set AI_CODE_REVIEWER_JWT_SECRET_KEY and "
            "AI_CODE_REVIEWER_SECRET_ENCRYPTION_KEY and "
            "AI_CODE_REVIEWER_BOOTSTRAP_ADMIN_PASSWORD before any non-local use."
        )
    await run_bootstrap()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
    )
