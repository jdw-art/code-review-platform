from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.models import User
from app.schemas.me import AccessContextResponse
from app.security.deps import get_current_user
from app.services.access_context import AccessContextService


router = APIRouter(prefix="/me", tags=["me"])


@router.get("/access-context", response_model=AccessContextResponse)
async def get_access_context(
    current_user: User = Depends(get_current_user),
    service: AccessContextService = Depends(),
) -> AccessContextResponse:
    return await service.get_access_context(current_user)
