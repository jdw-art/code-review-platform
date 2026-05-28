from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Menu, Permission, Project, ProjectTemplate, Role, User
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token


@pytest.fixture
def limited_project_templates_user_client(client, db_session):
    permission = Permission(
        name="Read Reviews",
        code="reviews.read",
        resource="reviews",
        action="read",
    )
    role = Role(
        name="Reviewer",
        code="project-template-reviewer",
        permissions=[permission],
    )
    user = User(
        username="project-template-limited-user",
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


def test_project_templates_api_supports_crud_status_and_options(
    authenticated_superuser_client,
    db_session,
):
    create_response = authenticated_superuser_client.post(
        "/api/v1/project-templates",
        json={
            "name": "Frontend Vue Template",
            "code": "frontend-vue-custom",
            "description": "Vue and TypeScript template",
            "file_extensions": [".vue", ".ts"],
            "review_prompt_template": "review frontend changes",
            "prompt_metadata": {"language": "zh-CN", "output_format": "markdown"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["id"], int)
    assert created["review_prompt_configured"] is True
    assert created["is_active"] is True

    list_response = authenticated_superuser_client.get(
        "/api/v1/project-templates",
        params={"page": 1, "page_size": 20},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(item["id"] == created["id"] for item in list_body["items"])

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/project-templates/{created['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["code"] == "frontend-vue-custom"

    update_response = authenticated_superuser_client.put(
        f"/api/v1/project-templates/{created['id']}",
        json={
            "name": "Frontend Vue Template Updated",
            "code": "frontend-vue-custom",
            "description": "Updated Vue template",
            "file_extensions": [".vue", ".ts", ".tsx"],
            "review_prompt_template": "",
            "prompt_metadata": {"language": "zh-CN", "output_format": "json"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Frontend Vue Template Updated"
    assert updated["review_prompt_configured"] is False

    status_response = authenticated_superuser_client.patch(
        f"/api/v1/project-templates/{created['id']}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    options_response = authenticated_superuser_client.get(
        "/api/v1/project-templates/options"
    )
    assert options_response.status_code == 200
    options_body = options_response.json()
    assert ".java" in options_body["common_file_extensions"]
    assert "review_dimensions" in options_body["prompt_metadata_presets"]

    stored_template = db_session.scalar(
        select(ProjectTemplate).where(ProjectTemplate.id == created["id"])
    )
    assert stored_template is not None
    assert stored_template.is_active is False


def test_project_templates_api_allows_creating_inactive_template(
    authenticated_superuser_client,
) -> None:
    response = authenticated_superuser_client.post(
        "/api/v1/project-templates",
        json={
            "name": "Inactive By Default Template",
            "code": "inactive-by-default-template",
            "description": "Created in disabled state",
            "file_extensions": [".py"],
            "review_prompt_template": "review python changes",
            "prompt_metadata": {"language": "zh-CN"},
            "is_active": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_active"] is False


def test_project_templates_api_rejects_duplicate_code(
    authenticated_superuser_client,
) -> None:
    first_response = authenticated_superuser_client.post(
        "/api/v1/project-templates",
        json={
            "name": "Unique Template",
            "code": "duplicate-template-code",
            "file_extensions": [".py"],
            "prompt_metadata": {},
        },
    )
    assert first_response.status_code == 201

    second_response = authenticated_superuser_client.post(
        "/api/v1/project-templates",
        json={
            "name": "Duplicate Template",
            "code": "duplicate-template-code",
            "file_extensions": [".ts"],
            "prompt_metadata": {},
        },
    )

    assert second_response.status_code == 409
    body = second_response.json()
    assert body["code"] == "PROJECT_TEMPLATE_CODE_ALREADY_EXISTS"


def test_project_templates_api_rejects_disabling_template_in_use(
    authenticated_superuser_client,
    db_session,
) -> None:
    template = ProjectTemplate(
        name="Bound Template",
        code="bound-template",
        file_extensions=[".py"],
        prompt_metadata={},
        is_active=True,
    )
    project = Project(
        name="Bound Project",
        key="bound-project",
        platform_type="gitlab",
        default_branch="main",
        template=template,
        is_active=True,
        review_enabled=True,
        settings={},
    )
    db_session.add_all([template, project])
    db_session.commit()

    response = authenticated_superuser_client.patch(
        f"/api/v1/project-templates/{template.id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PROJECT_TEMPLATE_IN_USE"


def test_project_templates_api_bootstrap_seeds_permissions_menus_and_templates(
    client,
    authenticated_superuser_client,
    db_session,
):
    del authenticated_superuser_client

    response = client.get("/api/v1/project-templates/options")

    assert response.status_code == 200

    permission_codes = set(
        db_session.scalars(select(Permission.code).order_by(Permission.code.asc())).all()
    )
    menu_names = set(db_session.scalars(select(Menu.name).order_by(Menu.id.asc())).all())
    template_codes = set(
        db_session.scalars(
            select(ProjectTemplate.code).order_by(ProjectTemplate.code.asc())
        ).all()
    )

    assert {
        "project:read",
        "project:create",
        "project:update",
        "project:status",
        "project_template:read",
        "project_template:create",
        "project_template:update",
        "project_template:status",
        "user:read",
        "user:create",
        "user:update",
        "user:delete",
        "user:status",
        "user:reset-password",
        "user:assign-role",
        "role:read",
        "role:create",
        "role:update",
        "role:delete",
        "role:assign",
        "menu:read",
        "menu:create",
        "menu:update",
        "menu:delete",
    }.issubset(permission_codes)
    assert {"项目管理", "项目模板管理", "权限管理", "用户管理", "角色管理"}.issubset(
        menu_names
    )
    assert {
        "java-default",
        "frontend-vue-ts",
        "go-default",
        "fullstack-common",
    }.issubset(template_codes)


def test_project_templates_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
):
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/project-templates"]["get"]
    assert operation["summary"] == "获取项目模板列表"
    assert "分页返回项目模板列表" in operation["description"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/project-templates", None),
        ("post", "/api/v1/project-templates", {"name": "No Access", "code": "no-access", "file_extensions": [".py"]}),
        ("get", "/api/v1/project-templates/options", None),
        ("get", "/api/v1/project-templates/999999", None),
        ("put", "/api/v1/project-templates/999999", {"name": "No Access", "code": "no-access", "file_extensions": [".py"], "prompt_metadata": {}}),
        ("patch", "/api/v1/project-templates/999999/status", {"is_active": False}),
    ],
)
def test_project_template_endpoints_require_permissions(
    limited_project_templates_user_client,
    method,
    path,
    payload,
):
    request_kwargs = {}
    if payload is not None:
        request_kwargs["json"] = payload

    response = getattr(limited_project_templates_user_client, method)(path, **request_kwargs)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert response.json()["message"] == "Forbidden."
