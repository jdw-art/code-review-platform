from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import RefreshSession, User
from app.db.session import get_db
from app.schemas.common import DomainUnauthorizedError
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenPairResponse
from app.security.passwords import hash_password, verify_password
from app.security.redis_store import RefreshSessionStore
from app.security.tokens import TokenError, decode_token, issue_access_token, issue_refresh_token

logger = logging.getLogger(__name__)


@lru_cache
def get_settings() -> Settings:
    """缓存并返回应用配置。"""
    return Settings()


@lru_cache
def get_redis_client() -> Redis:
    """创建并缓存 Redis 客户端。"""
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
    """构造 refresh token 会话存储对象。"""
    return RefreshSessionStore(redis_client)


def _invalid_credentials_error() -> DomainUnauthorizedError:
    return DomainUnauthorizedError(
        code="INVALID_CREDENTIALS",
        message="Invalid username or password.",
    )


def _invalid_refresh_token_error() -> DomainUnauthorizedError:
    return DomainUnauthorizedError(
        code="INVALID_REFRESH_TOKEN",
        message="Invalid or expired refresh token.",
    )


@dataclass(frozen=True)
class IssuedTokenPair:
    """封装一次签发得到的令牌对及其对应的会话 JTI。"""

    token_pair: TokenPairResponse
    session_jti: str


class AuthService:
    """封装登录、刷新、退出和修改密码等认证流程。"""

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
        """验证用户名密码并创建新的登录会话。"""
        statement = select(User).where(
            User.username == payload.username,
            User.is_active.is_(True),
        )
        user = self.session.scalar(statement)
        if user is None or not verify_password(payload.password, user.password_hash):
            logger.warning("Login failed for username=%s.", payload.username)
            raise _invalid_credentials_error()

        # 先创建刷新会话，再提交数据库；如果提交失败，需要回滚 Redis 中的会话记录。
        issued_token_pair = await self.issue_token_pair(user)
        user.last_login_at = datetime.now(UTC)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            await self._best_effort_revoke_store_session(
                issued_token_pair.session_jti,
                user.id,
                reason="login database commit failed after refresh session creation",
            )
            raise
        logger.info("Login succeeded for user_id=%s username=%s.", user.id, user.username)
        return issued_token_pair.token_pair

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        """轮换 refresh token，并返回新的令牌对。"""
        claims = self._decode_refresh_token(refresh_token)
        user_id = int(claims["sub"])
        session_jti = claims["jti"]

        user = self._get_active_user(user_id)
        await self._validate_store_session_owner(session_jti, user.id)
        refresh_session = self._get_refresh_session(
            user_id=user.id,
            session_jti=session_jti,
            refresh_token=refresh_token,
            require_active=True,
        )

        # 成功刷新后，旧 refresh token 会被标记为已替换，避免重复使用。
        issued_token_pair = await self.issue_token_pair(user)
        refresh_session.revoked_at = datetime.now(UTC)
        refresh_session.replaced_by_jti = issued_token_pair.session_jti
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            await self._best_effort_revoke_store_session(
                issued_token_pair.session_jti,
                user.id,
                reason="refresh database commit failed after replacement session creation",
            )
            raise

        await self._best_effort_revoke_store_session(
            session_jti,
            user.id,
            reason="refresh completed and replaced prior session",
        )
        logger.info("Refresh succeeded for user_id=%s.", user.id)
        return issued_token_pair.token_pair

    async def logout(self, user: User, refresh_token: str) -> None:
        """注销当前 refresh token 对应的会话。"""
        claims = self._decode_refresh_token(refresh_token)
        token_user_id = int(claims["sub"])
        session_jti = claims["jti"]
        if token_user_id != user.id:
            raise _invalid_refresh_token_error()

        await self._validate_store_session_owner(session_jti, user.id)
        refresh_session = self._get_refresh_session(
            user_id=user.id,
            session_jti=session_jti,
            refresh_token=refresh_token,
            require_active=True,
        )
        refresh_session.revoked_at = datetime.now(UTC)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        await self._best_effort_revoke_store_session(
            session_jti,
            user.id,
            reason="logout completed",
        )
        logger.info("Logout completed for user_id=%s.", user.id)

    async def logout_all(self, user: User) -> None:
        """注销当前用户的全部 refresh token 会话。"""
        self._mark_all_active_refresh_sessions_revoked(user.id)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        await self._best_effort_revoke_all_store_sessions(user.id)
        logger.info("Logout-all completed for user_id=%s.", user.id)

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        """修改当前用户密码并撤销全部 refresh token 会话。"""
        if not verify_password(payload.current_password, user.password_hash):
            raise _invalid_credentials_error()

        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        # 密码更新后，所有旧 refresh token 都必须失效，避免旧设备继续续期。
        self._mark_all_active_refresh_sessions_revoked(user.id)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        await self._best_effort_revoke_all_store_sessions(user.id)
        logger.info("Password changed for user_id=%s.", user.id)

    async def issue_token_pair(self, user: User) -> IssuedTokenPair:
        """签发新的 access/refresh token，并落库 refresh 会话。"""
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
        await self.refresh_store.save_refresh_session(
            session_jti,
            user.id,
            refresh_ttl_seconds,
        )
        return IssuedTokenPair(
            token_pair=TokenPairResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=access_ttl_seconds,
                must_change_password=user.must_change_password,
            ),
            session_jti=session_jti,
        )

    def _decode_refresh_token(self, refresh_token: str) -> dict:
        """解析并校验 refresh token。"""
        try:
            return decode_token(refresh_token, expected_token_type="refresh")
        except TokenError as exc:
            raise _invalid_refresh_token_error() from exc

    def _get_active_user(self, user_id: int) -> User:
        """获取仍处于启用状态的用户。"""
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
        """对 refresh token 做哈希后再持久化。"""
        return sha256(token.encode("utf-8")).hexdigest()

    def _get_refresh_session(
        self,
        *,
        user_id: int,
        session_jti: str,
        refresh_token: str,
        require_active: bool,
    ) -> RefreshSession:
        """按 JTI 读取 refresh 会话并校验其可用性。"""
        refresh_session = self.session.scalar(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.jti == session_jti,
            )
        )
        if refresh_session is None:
            raise _invalid_refresh_token_error()
        if refresh_session.refresh_token_hash != self._hash_token(refresh_token):
            raise _invalid_refresh_token_error()
        if require_active and refresh_session.revoked_at is not None:
            raise _invalid_refresh_token_error()
        return refresh_session

    def _mark_all_active_refresh_sessions_revoked(self, user_id: int) -> None:
        """将用户当前所有未撤销的 refresh 会话标记为已失效。"""
        active_sessions = self.session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
        ).all()
        revoked_at = datetime.now(UTC)
        for refresh_session in active_sessions:
            refresh_session.revoked_at = revoked_at

    async def _validate_store_session_owner(self, session_jti: str, user_id: int) -> None:
        """确认 Redis 中记录的 refresh 会话归属与当前用户一致。"""
        stored_user_id = await self.refresh_store.get_user_id_for_session(session_jti)
        if stored_user_id != user_id:
            raise _invalid_refresh_token_error()

    async def _best_effort_revoke_store_session(
        self,
        session_jti: str,
        user_id: int,
        *,
        reason: str,
    ) -> None:
        """尽力撤销单个 Redis refresh 会话，失败时仅记录日志。"""
        try:
            await self.refresh_store.revoke_refresh_session(session_jti, user_id)
        except Exception:
            logger.warning(
                "Failed to revoke refresh session in store after %s.",
                reason,
                exc_info=True,
            )

    async def _best_effort_revoke_all_store_sessions(self, user_id: int) -> None:
        """尽力撤销用户在 Redis 中的全部 refresh 会话，失败时仅记录日志。"""
        try:
            await self.refresh_store.revoke_all_user_sessions(user_id)
        except Exception:
            logger.warning(
                "Failed to revoke all refresh sessions in store after database commit.",
                exc_info=True,
            )
