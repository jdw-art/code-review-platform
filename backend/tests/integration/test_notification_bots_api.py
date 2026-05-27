from __future__ import annotations

from sqlalchemy import select

from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.models import AuditLog, NotificationBot


def test_notification_bots_api_supports_crud_status_and_encrypts_secret(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_response = authenticated_superuser_client.post(
        "/api/v1/notification-bots",
        json={
            "name": "DingTalk Bot",
            "bot_type": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send",
            "secret": "ding-secret-token",
            "mention_strategy": "all",
            "template_config": {"title": "Review Result"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["id"], int)
    assert created["secret_masked"] == "ding**********oken"
    assert "secret" not in created
    assert created["is_active"] is True

    stored_bot = db_session.scalar(
        select(NotificationBot).where(NotificationBot.id == created["id"])
    )
    assert stored_bot is not None
    assert stored_bot.secret_encrypted != "ding-secret-token"
    cipher = SecretCipher(Settings().secret_encryption_key)
    assert cipher.decrypt_text(str(stored_bot.secret_encrypted)) == "ding-secret-token"

    list_response = authenticated_superuser_client.get("/api/v1/notification-bots")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json()["items"])

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/notification-bots/{created['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["secret_masked"] == "ding**********oken"

    update_response = authenticated_superuser_client.put(
        f"/api/v1/notification-bots/{created['id']}",
        json={
            "name": "DingTalk Bot Updated",
            "bot_type": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send",
            "secret": "rotated-secret-token",
            "mention_strategy": "none",
            "template_config": {"title": "Updated"},
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "DingTalk Bot Updated"
    assert update_response.json()["secret_masked"] == "rota**********oken"

    status_response = authenticated_superuser_client.patch(
        f"/api/v1/notification-bots/{created['id']}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    audit_log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "notification_bot",
            AuditLog.resource_id == created["id"],
            AuditLog.action == "notification_bot.create",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_log is not None
    assert audit_log.request_payload["secret"] == "***"


def test_notification_bots_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
) -> None:
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/notification-bots"]["get"]
    assert operation["summary"] == "获取机器人列表"
    assert "分页返回通知机器人列表" in operation["description"]
