from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import RefreshSession, User
from app.db.session import get_db
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenPairResponse
from app.security.passwords import hash_password, verify_password
from app.security.redis_store import RefreshSessionStore
from app.security.tokens import TokenError, decode_token, issue_access_token, issue_refresh_token


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def get_refresh_session_store(
    redis_client: Redis = Depends(get_redis_client),
) -> RefreshSessionStore:
    return RefreshSessionStore(redis_client)


def _invalid_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )


def _invalid_refresh_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )


class AuthService:
    def __init__(
        self,
        session: Session = Depends(get_db),
        settings: Settings = Depends(get_settings),
        refresh_store: RefreshSessionStore = Depends(get_refresh_session_store),
    ) -> None:
        self.session = session
        self.settings = settings
        self.refresh_store = refresh_store

    async def login(self, payload: LoginRequest) -> TokenPairResponse:
        statement = select(User).where(
            User.username == payload.username,
            User.is_active.is_(True),
        )
        user = self.session.scalar(statement)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise _invalid_credentials_error()

        token_pair, _ = await self.issue_token_pair(user)
        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        return token_pair

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        claims = self._decode_refresh_token(refresh_token)
        user_id = int(claims["sub"])
        session_jti = claims["jti"]

        user = self._get_active_user(user_id)
        stored_user_id = await self.refresh_store.get_user_id_for_session(session_jti)
        if stored_user_id != user.id:
            raise _invalid_refresh_token_error()

        refresh_session = self.session.scalar(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id,
                RefreshSession.jti == session_jti,
            )
        )
        if refresh_session is None or refresh_session.revoked_at is not None:
            raise _invalid_refresh_token_error()
        if refresh_session.refresh_token_hash != self._hash_token(refresh_token):
            raise _invalid_refresh_token_error()

        token_pair, replacement_jti = await self.issue_token_pair(user)
        refresh_session.revoked_at = datetime.now(UTC)
        refresh_session.replaced_by_jti = replacement_jti
        await self.refresh_store.revoke_refresh_session(session_jti, user.id)
        self.session.commit()
        return token_pair

    async def logout(self, user: User, refresh_token: str) -> None:
        claims = self._decode_refresh_token(refresh_token)
        token_user_id = int(claims["sub"])
        session_jti = claims["jti"]
        if token_user_id != user.id:
            raise _invalid_refresh_token_error()

        refresh_session = self.session.scalar(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id,
                RefreshSession.jti == session_jti,
            )
        )
        if refresh_session is not None and refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(UTC)

        stored_user_id = await self.refresh_store.get_user_id_for_session(session_jti)
        if stored_user_id is not None and stored_user_id != user.id:
            raise _invalid_refresh_token_error()
        if stored_user_id == user.id:
            await self.refresh_store.revoke_refresh_session(session_jti, user.id)

        self.session.commit()

    async def logout_all(self, user: User) -> None:
        active_sessions = self.session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
        ).all()
        revoked_at = datetime.now(UTC)
        for refresh_session in active_sessions:
            refresh_session.revoked_at = revoked_at

        await self.refresh_store.revoke_all_user_sessions(user.id)
        self.session.commit()

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not verify_password(payload.current_password, user.password_hash):
            raise _invalid_credentials_error()

        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        await self.logout_all(user)

    async def issue_token_pair(self, user: User) -> tuple[TokenPairResponse, str]:
        session_jti = str(uuid4())
        now = datetime.now(UTC)
        access_token = issue_access_token(
            user_id=user.id,
            username=user.username,
            is_superuser=user.is_superuser,
        )
        refresh_token = issue_refresh_token(user_id=user.id, session_jti=session_jti)
        refresh_ttl_seconds = self.settings.refresh_token_ttl_days * 24 * 60 * 60
        access_ttl_seconds = self.settings.access_token_ttl_minutes * 60
        await self.refresh_store.save_refresh_session(
            session_jti,
            user.id,
            refresh_ttl_seconds,
        )
        self.session.add(
            RefreshSession(
                user_id=user.id,
                jti=session_jti,
                refresh_token_hash=self._hash_token(refresh_token),
                issued_at=now,
                expires_at=now + timedelta(days=self.settings.refresh_token_ttl_days),
            )
        )
        self.session.flush()
        return (
            TokenPairResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=access_ttl_seconds,
                must_change_password=user.must_change_password,
            ),
            session_jti,
        )

    def _decode_refresh_token(self, refresh_token: str) -> dict:
        try:
            return decode_token(refresh_token, expected_token_type="refresh")
        except TokenError as exc:
            raise _invalid_refresh_token_error() from exc

    def _get_active_user(self, user_id: int) -> User:
        user = self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )
        if user is None:
            raise _invalid_refresh_token_error()
        return user

    @staticmethod
    def _hash_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()
