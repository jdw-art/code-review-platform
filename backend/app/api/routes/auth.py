from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.db.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.security.deps import get_current_user
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(),
) -> TokenPairResponse:
    return await service.login(payload)


@router.post("/refresh", response_model=TokenPairResponse, status_code=status.HTTP_200_OK)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(),
) -> TokenPairResponse:
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    await service.logout(current_user, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    await service.logout_all(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(),
) -> Response:
    await service.change_password(current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
