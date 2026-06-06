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
        .where(AuditLog.action == "auth.login", AuditLog.resource_type == "auth")
        .order_by(AuditLog.id.desc())
    )
    assert stored_log is not None
    assert stored_log.request_payload["password"] == "***"

    list_response = authenticated_superuser_client.get(
        "/api/v1/audit-logs",
        params={"page": 1, "page_size": 20, "action": "auth.login"},
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

    assert {"user.create", "user.status", "user.reset_password"}.issubset(actions)
    create_log = next(log for log in logs if log.action == "user.create")
    reset_log = next(log for log in logs if log.action == "user.reset_password")
    assert create_log.request_payload["password"] == "***"
    assert reset_log.request_payload["new_password"] == "***"


def test_auth_session_actions_write_audit_logs(
    authenticated_default_password_client,
    default_password_token_pair,
    db_session,
) -> None:
    logout_response = authenticated_default_password_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": str(default_password_token_pair["refresh_token"])},
    )
    assert logout_response.status_code == 204

    second_login_response = authenticated_default_password_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    assert second_login_response.status_code == 200

    logout_all_response = authenticated_default_password_client.post("/api/v1/auth/logout-all")
    assert logout_all_response.status_code == 204

    change_password_response = authenticated_default_password_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "jdw112233",
            "new_password": "jdw112233-new",
        },
    )
    assert change_password_response.status_code == 204

    logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "auth")
        .order_by(AuditLog.id.asc())
    ).all()
    actions = {log.action for log in logs}

    assert {"auth.logout", "auth.logout_all", "auth.change_password"}.issubset(actions)
    logout_log = next(log for log in reversed(logs) if log.action == "auth.logout")
    change_password_log = next(
        log for log in reversed(logs) if log.action == "auth.change_password"
    )
    assert logout_log.request_payload["refresh_token"] == "***"
    assert change_password_log.request_payload["current_password"] == "***"
    assert change_password_log.request_payload["new_password"] == "***"


def test_logout_failure_writes_audit_log(
    authenticated_default_password_client,
    db_session,
) -> None:
    response = authenticated_default_password_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid-refresh-token"},
    )

    assert response.status_code == 401
    log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "auth",
            AuditLog.action == "auth.logout",
            AuditLog.result == "failure",
        )
        .order_by(AuditLog.id.desc())
    )
    assert log is not None
    assert log.response_status == 401
    assert log.request_payload["refresh_token"] == "***"


def test_change_password_failure_writes_audit_log(
    authenticated_default_password_client,
    db_session,
) -> None:
    response = authenticated_default_password_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "wrong-current-password",
            "new_password": "new-password-xyz",
        },
    )

    assert response.status_code == 401
    log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "auth",
            AuditLog.action == "auth.change_password",
            AuditLog.result == "failure",
        )
        .order_by(AuditLog.id.desc())
    )
    assert log is not None
    assert log.response_status == 401
    assert log.request_payload["current_password"] == "***"
    assert log.request_payload["new_password"] == "***"


def test_user_update_and_assign_role_actions_write_audit_logs(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_user_response = authenticated_superuser_client.post(
        "/api/v1/users",
        json={"username": "audited-editor", "password": "audited-password"},
    )
    assert create_user_response.status_code == 201
    created_user = create_user_response.json()

    create_role_response = authenticated_superuser_client.post(
        "/api/v1/roles",
        json={
            "name": "Audited Role",
            "code": "audited-role",
            "description": "role for audit coverage",
        },
    )
    assert create_role_response.status_code == 201
    created_role = create_role_response.json()

    update_response = authenticated_superuser_client.patch(
        f"/api/v1/users/{created_user['id']}",
        json={
            "nickname": "Audited Editor",
            "email": "audited-editor@example.com",
            "phone": "15500008888",
        },
    )
    assert update_response.status_code == 200

    assign_role_response = authenticated_superuser_client.put(
        f"/api/v1/users/{created_user['id']}/roles",
        json={"role_ids": [created_role["id"]]},
    )
    assert assign_role_response.status_code == 200

    logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "user",
            AuditLog.resource_id == created_user["id"],
        )
        .order_by(AuditLog.id.asc())
    ).all()
    actions = {log.action for log in logs}

    assert {"user.create", "user.update", "user.assign_role"}.issubset(actions)
    update_log = next(log for log in logs if log.action == "user.update")
    assign_log = next(log for log in logs if log.action == "user.assign_role")
    assert update_log.request_payload["nickname"] == "Audited Editor"
    assert assign_log.request_payload["role_ids"] == [created_role["id"]]


def test_role_permission_and_menu_actions_write_audit_logs(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_permission_response = authenticated_superuser_client.post(
        "/api/v1/permissions",
        json={
            "name": "Audit Permission",
            "code": "audit:test",
            "resource": "audit",
            "action": "read",
            "description": "permission for audit coverage",
        },
    )
    assert create_permission_response.status_code == 201
    permission = create_permission_response.json()

    update_permission_response = authenticated_superuser_client.patch(
        f"/api/v1/permissions/{permission['id']}",
        json={"description": "updated permission description"},
    )
    assert update_permission_response.status_code == 200

    create_menu_response = authenticated_superuser_client.post(
        "/api/v1/menus",
        json={
            "name": "Audit Menu",
            "path": "/audit-menu",
            "sort": 10,
            "visible": True,
            "icon": "radar",
        },
    )
    assert create_menu_response.status_code == 201
    menu = create_menu_response.json()

    update_menu_response = authenticated_superuser_client.patch(
        f"/api/v1/menus/{menu['id']}",
        json={"name": "Audit Menu Updated", "path": "/audit-menu-updated"},
    )
    assert update_menu_response.status_code == 200

    create_role_response = authenticated_superuser_client.post(
        "/api/v1/roles",
        json={
            "name": "Audit Role",
            "code": "audit-role",
            "description": "role for audit coverage",
        },
    )
    assert create_role_response.status_code == 201
    role = create_role_response.json()

    update_role_response = authenticated_superuser_client.patch(
        f"/api/v1/roles/{role['id']}",
        json={"name": "Audit Role Updated", "description": "updated role description"},
    )
    assert update_role_response.status_code == 200

    assign_permission_response = authenticated_superuser_client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_ids": [permission["id"]]},
    )
    assert assign_permission_response.status_code == 200

    assign_menu_response = authenticated_superuser_client.put(
        f"/api/v1/roles/{role['id']}/menus",
        json={"menu_ids": [menu["id"]]},
    )
    assert assign_menu_response.status_code == 200

    delete_role_response = authenticated_superuser_client.delete(f"/api/v1/roles/{role['id']}")
    assert delete_role_response.status_code == 204

    delete_permission_response = authenticated_superuser_client.delete(
        f"/api/v1/permissions/{permission['id']}"
    )
    assert delete_permission_response.status_code == 204

    delete_menu_response = authenticated_superuser_client.delete(f"/api/v1/menus/{menu['id']}")
    assert delete_menu_response.status_code == 204

    role_logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "role", AuditLog.resource_id == role["id"])
        .order_by(AuditLog.id.asc())
    ).all()
    permission_logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "permission",
            AuditLog.resource_id == permission["id"],
        )
        .order_by(AuditLog.id.asc())
    ).all()
    menu_logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "menu", AuditLog.resource_id == menu["id"])
        .order_by(AuditLog.id.asc())
    ).all()

    assert {
        "role.create",
        "role.update",
        "role.assign_permission",
        "role.assign_menu",
        "role.delete",
    }.issubset({log.action for log in role_logs})
    assert {
        "permission.create",
        "permission.update",
        "permission.delete",
    }.issubset({log.action for log in permission_logs})
    assert {
        "menu.create",
        "menu.update",
        "menu.delete",
    }.issubset({log.action for log in menu_logs})


def test_model_and_bot_mutation_actions_write_audit_logs(
    authenticated_superuser_client,
    db_session,
) -> None:
    create_model_response = authenticated_superuser_client.post(
        "/api/v1/models",
        json={
            "name": "Audit Model",
            "provider": "openai",
            "model_code": "gpt-4.1",
            "api_key": "sk-audit-model-secret",
            "is_default": False,
        },
    )
    assert create_model_response.status_code == 201
    model = create_model_response.json()

    update_model_response = authenticated_superuser_client.put(
        f"/api/v1/models/{model['id']}",
        json={
            "name": "Audit Model Updated",
            "provider": "openai",
            "model_code": "gpt-4.1-mini",
            "api_key": "sk-updated-model-secret",
            "temperature": 0.3,
            "max_tokens": 2048,
            "top_p": 0.8,
            "prompt_template": "review updated model",
            "is_default": False,
            "is_active": True,
        },
    )
    assert update_model_response.status_code == 200

    model_status_response = authenticated_superuser_client.patch(
        f"/api/v1/models/{model['id']}/status",
        json={"is_active": False},
    )
    assert model_status_response.status_code == 200

    create_bot_response = authenticated_superuser_client.post(
        "/api/v1/notification-bots",
        json={
            "name": "Audit Bot",
            "bot_type": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send",
            "secret": "audit-bot-secret",
            "mention_strategy": "all",
            "template_config": {"title": "Audit"},
        },
    )
    assert create_bot_response.status_code == 201
    bot = create_bot_response.json()

    update_bot_response = authenticated_superuser_client.put(
        f"/api/v1/notification-bots/{bot['id']}",
        json={
            "name": "Audit Bot Updated",
            "bot_type": "dingtalk",
            "webhook_url": "https://oapi.dingtalk.com/robot/send",
            "secret": "updated-bot-secret",
            "mention_strategy": "none",
            "template_config": {"title": "Audit Updated"},
            "is_active": True,
        },
    )
    assert update_bot_response.status_code == 200

    bot_status_response = authenticated_superuser_client.patch(
        f"/api/v1/notification-bots/{bot['id']}/status",
        json={"is_active": False},
    )
    assert bot_status_response.status_code == 200

    model_logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "llm_model",
            AuditLog.resource_id == model["id"],
        )
        .order_by(AuditLog.id.asc())
    ).all()
    bot_logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "notification_bot",
            AuditLog.resource_id == bot["id"],
        )
        .order_by(AuditLog.id.asc())
    ).all()

    assert {
        "llm_model.create",
        "llm_model.update",
        "llm_model.status",
    }.issubset({log.action for log in model_logs})
    assert {
        "notification_bot.create",
        "notification_bot.update",
        "notification_bot.status",
    }.issubset({log.action for log in bot_logs})

    model_update_log = next(log for log in model_logs if log.action == "llm_model.update")
    bot_update_log = next(log for log in bot_logs if log.action == "notification_bot.update")
    assert model_update_log.request_payload["api_key"] == "***"
    assert bot_update_log.request_payload["secret"] == "***"


def test_purge_audit_logs_keeps_system_audit_entry(
    authenticated_superuser_client,
    db_session,
) -> None:
    business_log = AuditLog(
        username_snapshot="root-admin",
        action="user.create",
        resource_type="user",
        resource_id=101,
        resource_name_snapshot="temp-user",
        request_path="/api/v1/users",
        request_method="POST",
        request_payload={"username": "temp-user"},
        response_status=201,
        result="success",
    )
    system_log = AuditLog(
        username_snapshot="system",
        action="audit_log.seed",
        resource_type="audit_log",
        resource_id=1,
        resource_name_snapshot="seed",
        request_path="/api/v1/audit-logs",
        request_method="GET",
        request_payload={},
        response_status=200,
        result="success",
    )
    db_session.add_all([business_log, system_log])
    db_session.commit()

    response = authenticated_superuser_client.post("/api/v1/audit-logs/purge")

    assert response.status_code == 202
    payload = response.json()
    assert payload["purged_count"] >= 1

    remaining_logs = db_session.scalars(select(AuditLog).order_by(AuditLog.id.asc())).all()
    actions = {log.action for log in remaining_logs}
    resource_types = {log.resource_type for log in remaining_logs}

    assert "user.create" not in actions
    assert "audit_log.seed" in actions
    assert "audit_log.purge" in actions
    assert resource_types == {"audit_log"}

    purge_log = next(log for log in remaining_logs if log.action == "audit_log.purge")
    assert purge_log.request_payload["purged_count"] == payload["purged_count"]
    assert purge_log.result == "success"
