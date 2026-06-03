from __future__ import annotations

from sqlalchemy import select

from app.db.models import Permission, Project, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


def _ensure_permission(db_session, *, code: str, name: str, resource: str, action: str) -> Permission:
    permission = db_session.scalar(select(Permission).where(Permission.code == code))
    if permission is not None:
        return permission
    permission = Permission(
        name=name,
        code=code,
        resource=resource,
        action=action,
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


def _create_authed_client(client, db_session, *, username: str, permission_codes: list[str]):
    permissions = [
        _ensure_permission(
            db_session,
            code=code,
            name=code,
            resource=code.split(":", 1)[0],
            action=code.split(":", 1)[1] if ":" in code else "read",
        )
        for code in permission_codes
    ]
    role = Role(
        name=f"{username}-role",
        code=f"{username}-role",
        permissions=permissions,
    )
    user = User(
        username=username,
        password_hash=hash_password("agent-password"),
        is_active=True,
        is_superuser=False,
        must_change_password=False,
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    access_token = issue_access_token(
        user_id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
    )
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


def _create_project(db_session) -> Project:
    project = Project(
        name="Agent Project",
        key="agent-project",
        platform_type="github",
        repo_url="https://example.com/agent-project.git",
        default_branch="main",
        description="Project for repo assistant API tests",
        review_enabled=True,
        settings={},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_agent_session_message_and_run_flow(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)

    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "仓库理解助手"},
    )

    assert session_response.status_code == 201
    session_body = session_response.json()
    assert isinstance(session_body["id"], int)

    message_response = authenticated_superuser_client.post(
        f"/api/v1/agent/sessions/{session_body['id']}/messages",
        json={"content": "帮我总结一下仓库。"},
    )

    assert message_response.status_code == 201
    message_body = message_response.json()
    assert isinstance(message_body["user_message_id"], int)
    assert isinstance(message_body["assistant_message_id"], int)
    assert isinstance(message_body["run_id"], int)

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/agent/sessions/{session_body['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["project_id"] == project.id

    messages_response = authenticated_superuser_client.get(
        f"/api/v1/agent/sessions/{session_body['id']}/messages"
    )
    assert messages_response.status_code == 200
    assert len(messages_response.json()) == 2

    run_response = authenticated_superuser_client.get(
        f"/api/v1/agent/runs/{message_body['run_id']}"
    )
    assert run_response.status_code == 200
    assert run_response.json()["id"] == message_body["run_id"]


def test_agent_endpoints_require_project_read_permission(
    client,
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)
    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "No Access Session"},
    )
    session_id = session_response.json()["id"]

    limited_client = _create_authed_client(
        client,
        db_session,
        username="agent-limited-user",
        permission_codes=["reviews.read"],
    )

    list_response = limited_client.get(f"/api/v1/projects/{project.id}/agent/sessions")
    assert list_response.status_code == 403
    assert list_response.json()["code"] == "FORBIDDEN"

    message_response = limited_client.post(
        f"/api/v1/agent/sessions/{session_id}/messages",
        json={"content": "能看吗？"},
    )
    assert message_response.status_code == 403
    assert message_response.json()["code"] == "FORBIDDEN"


def test_agent_snapshot_refresh_requires_project_update_permission(
    client,
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)
    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "Read Only Session"},
    )
    session_id = session_response.json()["id"]

    read_only_client = _create_authed_client(
        client,
        db_session,
        username="agent-read-user",
        permission_codes=["project:read"],
    )

    response = read_only_client.post(
        f"/api/v1/agent/sessions/{session_id}/snapshot/refresh"
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
