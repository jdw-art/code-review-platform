from __future__ import annotations

from sqlalchemy import select

from app.core.config import Settings
from app.db.models import Role, User
from app.db.models.role import SYSTEM_SUPER_ADMIN_ROLE_CODE, SYSTEM_SUPER_ADMIN_ROLE_NAME
from app.security.passwords import hash_password


def build_bootstrap_admin_payload() -> dict[str, object]:
    settings = Settings()
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


def _get_or_create_super_admin_role() -> Role:
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        role = session.scalar(
            select(Role).where(Role.code == SYSTEM_SUPER_ADMIN_ROLE_CODE)
        )
        if role is None:
            role = Role(**build_super_admin_role_payload())
            session.add(role)
            session.commit()
            session.refresh(role)
        return role


def _bootstrap_admin_exists(session) -> User | None:
    settings = Settings()
    return session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )


def _ensure_bootstrap_admin_role(session, user: User, role: Role) -> None:
    if any(existing_role.id == role.id for existing_role in user.roles):
        return

    attached_role = session.merge(role)
    user.roles.append(attached_role)


def bootstrap_initial_admin() -> None:
    from app.db.session import SessionLocal

    role = _get_or_create_super_admin_role()
    with SessionLocal() as session:
        user = _bootstrap_admin_exists(session)
        if user is None:
            user = User(**build_bootstrap_admin_payload())
            session.add(user)
            session.flush()

        _ensure_bootstrap_admin_role(session, user, role)
        session.commit()


async def run_bootstrap() -> None:
    bootstrap_initial_admin()
