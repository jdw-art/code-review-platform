from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Role, User
from app.db.models.role import SYSTEM_SUPER_ADMIN_ROLE_CODE, SYSTEM_SUPER_ADMIN_ROLE_NAME
from app.db.session import SessionLocal
from app.security.passwords import hash_password

SessionFactory = Callable[[], Session]


def build_bootstrap_admin_payload(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or Settings()
    return {
        "username": settings.bootstrap_admin_username,
        "password_hash": hash_password(settings.bootstrap_admin_password),
        "is_active": True,
        "is_superuser": True,
        "must_change_password": True,
    }


def build_super_admin_role_payload() -> dict[str, object]:
    return {
        "name": SYSTEM_SUPER_ADMIN_ROLE_NAME,
        "code": SYSTEM_SUPER_ADMIN_ROLE_CODE,
        "description": "System bootstrap role with full administrative access.",
        "is_system": True,
    }


def _get_or_create_super_admin_role(session: Session) -> Role:
    role = session.scalar(
        select(Role).where(Role.code == SYSTEM_SUPER_ADMIN_ROLE_CODE)
    )
    if role is None:
        role = Role(**build_super_admin_role_payload())
        session.add(role)
        session.flush()
    return role


def _get_or_create_bootstrap_admin(session: Session, settings: Settings) -> User:
    user = session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )
    if user is None:
        user = User(**build_bootstrap_admin_payload(settings))
        session.add(user)
        session.flush()
    return user


def _ensure_bootstrap_admin_role(user: User, role: Role) -> None:
    if any(existing_role.code == role.code for existing_role in user.roles):
        return
    user.roles.append(role)


def _bootstrap_once(session: Session, settings: Settings) -> None:
    role = _get_or_create_super_admin_role(session)
    user = _get_or_create_bootstrap_admin(session, settings)
    _ensure_bootstrap_admin_role(user, role)


def bootstrap_initial_admin(
    *,
    session_factory: SessionFactory = SessionLocal,
    settings: Settings | None = None,
    max_attempts: int = 2,
) -> None:
    settings = settings or Settings()

    for attempt in range(max_attempts):
        with session_factory() as session:
            try:
                with session.begin():
                    _bootstrap_once(session, settings)
                return
            except IntegrityError:
                if attempt == max_attempts - 1:
                    raise


async def run_bootstrap() -> None:
    bootstrap_initial_admin()
