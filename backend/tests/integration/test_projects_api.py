from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Permission, Project, ProjectTemplate, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def active_template(db_session) -> ProjectTemplate:
    template = ProjectTemplate(
        name="Java Default",
        code="java-default-custom",
        description="Java backend template",
        file_extensions=[".java", ".xml"],
        review_prompt_template="review java changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def inactive_template(db_session) -> ProjectTemplate:
    template = ProjectTemplate(
        name="Inactive Template",
        code="inactive-template-custom",
        description="Disabled template",
        file_extensions=[".go"],
        review_prompt_template="review go changes",
        prompt_metadata={},
        is_system=False,
        is_active=False,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def limited_projects_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    role = Role(
        name="Reviewer",
        code="project-reviewer",
        permissions=[permission],
    )
    user = User(
        username="project-limited-user",
        password_hash=hash_password("limited-password"),
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


def test_projects_api_supports_crud_status_and_options(
    authenticated_superuser_client,
    active_template,
    db_session,
):
    create_response = authenticated_superuser_client.post(
        "/api/v1/projects",
        json={
            "name": "Demo Project",
            "key": "demo-project",
            "platform_type": "gitlab",
            "repo_url": "https://example.com/demo.git",
            "default_branch": "main",
            "description": "Project for admin console tests",
            "template_id": active_template.id,
            "review_enabled": True,
            "settings": {"language": "java"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["id"], int)
    assert created["template"]["id"] == active_template.id
    assert created["review_enabled"] is True

    list_response = authenticated_superuser_client.get(
        "/api/v1/projects",
        params={"page": 1, "page_size": 20},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(item["id"] == created["id"] for item in list_body["items"])

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/projects/{created['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["key"] == "demo-project"

    update_response = authenticated_superuser_client.put(
        f"/api/v1/projects/{created['id']}",
        json={
            "name": "Demo Project Updated",
            "key": "demo-project",
            "platform_type": "github",
            "repo_url": "https://example.com/demo-updated.git",
            "default_branch": "develop",
            "description": "Updated project",
            "template_id": active_template.id,
            "review_enabled": False,
            "settings": {"language": "typescript"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Demo Project Updated"
    assert updated["platform_type"] == "github"
    assert updated["review_enabled"] is False

    status_response = authenticated_superuser_client.patch(
        f"/api/v1/projects/{created['id']}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    options_response = authenticated_superuser_client.get("/api/v1/projects/options")
    assert options_response.status_code == 200
    options_body = options_response.json()
    assert {option["value"] for option in options_body["platform_types"]} >= {
        "gitlab",
        "github",
    }
    assert any(
        item["id"] == active_template.id for item in options_body["template_options"]
    )

    stored_project = db_session.scalar(select(Project).where(Project.id == created["id"]))
    assert stored_project is not None
    assert stored_project.is_active is False


def test_projects_api_rejects_inactive_template_binding(
    authenticated_superuser_client,
    inactive_template,
) -> None:
    response = authenticated_superuser_client.post(
        "/api/v1/projects",
        json={
            "name": "Inactive Template Project",
            "key": "inactive-template-project",
            "platform_type": "gitlab",
            "default_branch": "main",
            "template_id": inactive_template.id,
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PROJECT_TEMPLATE_INACTIVE"
    assert body["message"] == "项目模板未启用，不能绑定到项目。"


def test_projects_api_exposes_chinese_openapi(client, authenticated_superuser_client):
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/projects"]["get"]
    assert operation["summary"] == "获取项目列表"
    assert "分页返回后台项目列表" in operation["description"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/projects", None),
        ("post", "/api/v1/projects", {"name": "No Access", "key": "no-access", "platform_type": "gitlab", "default_branch": "main"}),
        ("get", "/api/v1/projects/options", None),
        ("get", "/api/v1/projects/999999", None),
        ("put", "/api/v1/projects/999999", {"name": "No Access", "key": "no-access", "platform_type": "gitlab", "default_branch": "main", "review_enabled": True, "settings": {}}),
        ("patch", "/api/v1/projects/999999/status", {"is_active": False}),
    ],
)
def test_project_management_endpoints_require_permissions(
    limited_projects_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload

    response = getattr(limited_projects_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
