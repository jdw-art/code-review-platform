from __future__ import annotations

from fastapi import Request
from sqlalchemy import select

from app.db.models import AuditLog, User
from app.schemas.audit_log import AuditActionContext
from app.services.audit_log_service import AuditLogService, sanitize_request_payload


def test_sanitize_request_payload_masks_nested_sensitive_fields() -> None:
    payload = {
        "username": "alice",
        "password": "raw-password",
        "profile": {
            "api_key": "sk-test",
            "nested": [{"token": "token-value"}, {"safe": "visible"}],
        },
        "refresh_token": "refresh-value",
    }

    sanitized = sanitize_request_payload(payload)

    assert sanitized["username"] == "alice"
    assert sanitized["password"] == "***"
    assert sanitized["profile"]["api_key"] == "***"
    assert sanitized["profile"]["nested"][0]["token"] == "***"
    assert sanitized["profile"]["nested"][1]["safe"] == "visible"
    assert sanitized["refresh_token"] == "***"


def test_record_action_persists_sanitized_audit_log(db_session) -> None:
    user = User(
        username="audit-admin",
        password_hash="hashed-password",
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    service = AuditLogService(session=db_session)
    context = AuditActionContext(
        user_id=user.id,
        username=user.username,
        action="auth.change_password",
        resource_type="auth",
        resource_id=user.id,
        resource_name="audit-admin",
        request_path="/api/v1/auth/change-password",
        request_method="POST",
        request_payload={
            "current_password": "old-password",
            "new_password": "new-password",
        },
        response_status=204,
        result="success",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    result = service.record_action(context, commit=True)

    stored = db_session.scalar(select(AuditLog).where(AuditLog.id == result.id))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.username_snapshot == "audit-admin"
    assert stored.request_payload == {
        "current_password": "***",
        "new_password": "***",
    }
    assert stored.result == "success"


def test_build_context_from_request_uses_client_and_current_user(db_session) -> None:
    user = User(
        username="request-user",
        password_hash="hashed-password",
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    request = Request(
        {
            "type": "http",
            "method": "PATCH",
            "path": "/api/v1/users/1/status",
            "headers": [(b"user-agent", b"pytest-agent")],
            "client": ("10.0.0.1", 12345),
        }
    )

    context = AuditLogService.build_context(
        request=request,
        current_user=user,
        action="user.status",
        resource_type="user",
        resource_id=1,
        resource_name="request-user",
        payload={"token": "secret-token", "is_active": False},
        response_status=200,
    )

    assert context.user_id == user.id
    assert context.username == "request-user"
    assert context.request_method == "PATCH"
    assert context.request_path == "/api/v1/users/1/status"
    assert context.ip_address == "10.0.0.1"
    assert context.user_agent == "pytest-agent"
    assert context.request_payload["token"] == "***"
    assert context.request_payload["is_active"] is False
