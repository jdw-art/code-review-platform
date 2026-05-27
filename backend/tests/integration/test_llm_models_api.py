from __future__ import annotations

from sqlalchemy import select

from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.models import AuditLog, LlmModel


def test_llm_models_api_supports_crud_status_and_encrypts_api_key(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_response = authenticated_superuser_client.post(
        "/api/v1/llm-models",
        json={
            "name": "OpenAI GPT 4.1",
            "provider": "openai",
            "model_code": "gpt-4.1",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-live-secret-key",
            "temperature": 0.2,
            "max_tokens": 4096,
            "top_p": 0.9,
            "prompt_template": "review code",
            "is_default": True,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["id"], int)
    assert created["api_key_masked"] == "sk-l**********-key"
    assert "api_key" not in created
    assert created["is_default"] is True
    assert created["is_active"] is True

    stored_model = db_session.scalar(
        select(LlmModel).where(LlmModel.id == created["id"])
    )
    assert stored_model is not None
    assert stored_model.api_key_encrypted != "sk-live-secret-key"
    cipher = SecretCipher(Settings().secret_encryption_key)
    assert cipher.decrypt_text(str(stored_model.api_key_encrypted)) == "sk-live-secret-key"

    list_response = authenticated_superuser_client.get("/api/v1/llm-models")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json()["items"])

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/llm-models/{created['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["api_key_masked"] == "sk-l**********-key"

    update_response = authenticated_superuser_client.put(
        f"/api/v1/llm-models/{created['id']}",
        json={
            "name": "OpenAI GPT 4.1 Updated",
            "provider": "openai",
            "model_code": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-rotated-secret-key",
            "temperature": 0.1,
            "max_tokens": 2048,
            "top_p": 1.0,
            "prompt_template": "review updated code",
            "is_default": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "OpenAI GPT 4.1 Updated"
    assert update_response.json()["api_key_masked"] == "sk-r**********-key"

    status_response = authenticated_superuser_client.patch(
        f"/api/v1/llm-models/{created['id']}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    audit_log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "llm_model",
            AuditLog.resource_id == created["id"],
            AuditLog.action == "create",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_log is not None
    assert audit_log.request_payload["api_key"] == "***"


def test_llm_models_api_allows_only_one_default(
    authenticated_superuser_client,
) -> None:
    first_response = authenticated_superuser_client.post(
        "/api/v1/llm-models",
        json={
            "name": "Default Model",
            "provider": "openai",
            "model_code": "gpt-4.1",
            "api_key": "first-secret",
            "is_default": True,
        },
    )
    assert first_response.status_code == 201

    second_response = authenticated_superuser_client.post(
        "/api/v1/llm-models",
        json={
            "name": "Second Default Model",
            "provider": "openai",
            "model_code": "gpt-4.1-mini",
            "api_key": "second-secret",
            "is_default": True,
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["code"] == "LLM_MODEL_DEFAULT_ALREADY_EXISTS"
