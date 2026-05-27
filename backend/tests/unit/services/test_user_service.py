from __future__ import annotations

import anyio

from app.db.models import User
from app.schemas.user import UserStatusUpdateRequest
from app.security.passwords import hash_password
from app.services.audit_log_service import AuditLogService
from app.services.user_service import UserService


class ExplodingRefreshSessionStore:
    async def revoke_all_user_sessions(self, user_id: int) -> int:
        del user_id
        raise RuntimeError("redis unavailable")


def test_update_status_treats_refresh_store_failure_as_best_effort(db_session) -> None:
    admin_user = User(
        username="status-admin",
        password_hash=hash_password("status-admin-password"),
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    target_user = User(
        username="status-target",
        password_hash=hash_password("status-target-password"),
        is_active=True,
        is_superuser=False,
        must_change_password=False,
    )
    db_session.add_all([admin_user, target_user])
    db_session.commit()
    db_session.refresh(admin_user)
    db_session.refresh(target_user)

    service = UserService(
        session=db_session,
        refresh_store=ExplodingRefreshSessionStore(),
        audit_log_service=AuditLogService(session=db_session),
    )

    result = anyio.run(
        service.update_status,
        admin_user,
        target_user.id,
        UserStatusUpdateRequest(is_active=False),
    )

    assert result.is_active is False
    db_session.refresh(target_user)
    assert target_user.is_active is False
