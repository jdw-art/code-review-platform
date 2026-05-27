from __future__ import annotations

from sqlalchemy import select

from app.db.models import AuditLog


def test_audit_logs_api_lists_and_gets_sanitized_logs(
    authenticated_superuser_client,
    db_session,
) -> None:
    login_response = authenticated_superuser_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    assert login_response.status_code == 200

    stored_log = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "login", AuditLog.resource_type == "auth")
        .order_by(AuditLog.id.desc())
    )
    assert stored_log is not None
    assert stored_log.request_payload["password"] == "***"

    list_response = authenticated_superuser_client.get(
        "/api/v1/audit-logs",
        params={"page": 1, "page_size": 20, "action": "login"},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    listed = next(item for item in list_body["items"] if item["id"] == stored_log.id)
    assert listed["request_payload"]["password"] == "***"

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/audit-logs/{stored_log.id}"
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["id"] == stored_log.id
    assert detail_body["username_snapshot"] == "admin"
    assert detail_body["request_payload"]["password"] == "***"


def test_user_change_actions_write_audit_logs(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_response = authenticated_superuser_client.post(
        "/api/v1/users",
        json={"username": "audited-user", "password": "audited-password"},
    )
    assert create_response.status_code == 201
    created_user = create_response.json()

    status_response = authenticated_superuser_client.patch(
        f"/api/v1/users/{created_user['id']}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200

    reset_response = authenticated_superuser_client.post(
        f"/api/v1/users/{created_user['id']}/reset-password",
        json={"new_password": "new-password-123"},
    )
    assert reset_response.status_code == 204

    logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "user",
            AuditLog.resource_id == created_user["id"],
        )
        .order_by(AuditLog.id.asc())
    ).all()
    actions = {log.action for log in logs}

    assert {"create", "status", "reset-password"}.issubset(actions)
    create_log = next(log for log in logs if log.action == "create")
    reset_log = next(log for log in logs if log.action == "reset-password")
    assert create_log.request_payload["password"] == "***"
    assert reset_log.request_payload["new_password"] == "***"
