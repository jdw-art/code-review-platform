from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db.models import Permission, Project, ProjectTemplate, ReviewRecord, Role, User
from app.main import app
from app.security.passwords import hash_password
from app.security.tokens import issue_access_token
from app.services.review_queue_service import get_review_queue_service


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


class FakeReviewQueueService:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def enqueue(
        self,
        *,
        review_record_id: int,
        platform_type: str,
        attempt: int = 1,
    ) -> str:
        self.messages.append(
            {
                "review_record_id": review_record_id,
                "platform_type": platform_type,
                "attempt": attempt,
            }
        )
        return f"{review_record_id}:{platform_type}:{attempt}"

    async def remove_message(self, raw_message: str) -> bool:
        del raw_message
        return True


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
            "settings": {
                "language": "java",
                "owner": "backend-team",
                "external_project_id": "1001",
                "gitlab_project_path": "acme/demo-project",
            },
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["id"], int)
    assert created["template"]["id"] == active_template.id
    assert created["review_enabled"] is True
    assert created["language"] == "java"
    assert created["owner"] == "backend-team"

    db_session.add_all(
        [
            ReviewRecord(
                project_id=created["id"],
                event_type="push",
                platform_type="gitlab",
                project_name_snapshot="Demo Project",
                author="alice",
                branch="main",
                review_status="reviewed",
                score=92,
                created_at=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
            ),
            ReviewRecord(
                project_id=created["id"],
                event_type="push",
                platform_type="gitlab",
                project_name_snapshot="Demo Project",
                author="bob",
                branch="main",
                review_status="reviewed",
                score=88,
                created_at=datetime(2026, 6, 4, 10, 30, tzinfo=timezone.utc),
                updated_at=datetime(2026, 6, 4, 10, 30, tzinfo=timezone.utc),
            ),
        ]
    )
    db_session.commit()

    list_response = authenticated_superuser_client.get(
        "/api/v1/projects",
        params={"page": 1, "page_size": 20},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    listed = next(item for item in list_body["items"] if item["id"] == created["id"])
    assert listed["language"] == "java"
    assert listed["owner"] == "backend-team"
    assert listed["score_average"] == 90.0
    assert listed["last_review_at"] == "2026-06-04T10:30:00Z"

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/projects/{created['id']}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["key"] == "demo-project"
    assert detail["score_average"] == 90.0
    assert detail["last_review_at"] == "2026-06-04T10:30:00Z"

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
            "settings": {
                "language": "typescript",
                "owner": "backend-team",
                "external_project_id": "9001",
                "external_repo_full_name": "acme/demo-project",
                "protected_branches": ["main", "release"],
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Demo Project Updated"
    assert updated["platform_type"] == "github"
    assert updated["review_enabled"] is False
    assert updated["owner"] == "backend-team"

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
    assert stored_project.settings == {
        "language": "typescript",
        "owner": "backend-team",
        "external_project_id": "9001",
        "external_repo_full_name": "acme/demo-project",
        "protected_branches": ["main", "release"],
    }


def test_projects_api_supports_server_side_search_and_language_filters(
    authenticated_superuser_client,
    db_session,
) -> None:
    db_session.add_all(
        [
            Project(
                name="Alpha Service",
                key="alpha-service",
                platform_type="gitlab",
                repo_url="https://example.com/alpha-service.git",
                default_branch="main",
                description="Primary Python service",
                review_enabled=True,
                settings={"language": "Python", "owner": "team-a"},
            ),
            Project(
                name="Beta Console",
                key="beta-console",
                platform_type="github",
                repo_url="https://example.com/beta-console.git",
                default_branch="main",
                description="TypeScript management console",
                review_enabled=True,
                settings={"language": "TypeScript", "owner": "team-b"},
            ),
            Project(
                name="Gamma Worker",
                key="gamma-worker",
                platform_type="gitlab",
                repo_url="https://example.com/gamma-worker.git",
                default_branch="develop",
                description="Async Python worker",
                review_enabled=True,
                settings={"language": "Python", "owner": "team-c"},
            ),
        ]
    )
    db_session.commit()

    search_response = authenticated_superuser_client.get(
        "/api/v1/projects",
        params={"page": 1, "page_size": 20, "search": "console"},
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["total"] == 1
    assert [item["name"] for item in search_body["items"]] == ["Beta Console"]

    language_response = authenticated_superuser_client.get(
        "/api/v1/projects",
        params={"page": 1, "page_size": 20, "language": "python"},
    )

    assert language_response.status_code == 200
    language_body = language_response.json()
    assert language_body["total"] == 2
    assert [item["name"] for item in language_body["items"]] == [
        "Alpha Service",
        "Gamma Worker",
    ]

    combined_response = authenticated_superuser_client.get(
        "/api/v1/projects",
        params={
            "page": 1,
            "page_size": 20,
            "search": "worker",
            "language": "Python",
        },
    )

    assert combined_response.status_code == 200
    combined_body = combined_response.json()
    assert combined_body["total"] == 1
    assert [item["name"] for item in combined_body["items"]] == ["Gamma Worker"]


def test_projects_api_supports_delete_and_cascades_review_records(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = Project(
        name="Delete Project",
        key="delete-project",
        platform_type="gitlab",
        repo_url="https://example.com/delete-project.git",
        default_branch="main",
        review_enabled=True,
        settings={"external_project_id": "2002"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    review_record = ReviewRecord(
        project_id=project.id,
        event_type="push",
        platform_type="gitlab",
        project_name_snapshot=project.name,
        author="alice",
        branch="main",
        review_status="queued",
    )
    db_session.add(review_record)
    db_session.commit()
    db_session.refresh(review_record)

    response = authenticated_superuser_client.delete(f"/api/v1/projects/{project.id}")

    assert response.status_code == 204
    assert db_session.scalar(select(Project).where(Project.id == project.id)) is None
    assert (
        db_session.scalar(select(ReviewRecord).where(ReviewRecord.id == review_record.id))
        is None
    )


def test_projects_api_supports_manual_review_trigger(
    authenticated_superuser_client,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.project_review_service import ProjectReviewService

    project = Project(
        name="Manual Review Project",
        key="manual-review-project",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/manual-review-project",
        default_branch="main",
        review_enabled=False,
        settings={
            "language": "python",
            "owner": "qa-team",
            "external_project_id": "3003",
            "gitlab_project_path": "acme/manual-review-project",
        },
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    queue_service = FakeReviewQueueService()
    app.dependency_overrides[get_review_queue_service] = lambda: queue_service
    monkeypatch.setattr(
        ProjectReviewService,
        "_resolve_default_branch_head",
        lambda self, project: "sha-main-001",
    )

    try:
        response = authenticated_superuser_client.post(
            f"/api/v1/projects/{project.id}/manual-review"
        )
    finally:
        app.dependency_overrides.pop(get_review_queue_service, None)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["branch"] == "main"
    assert body["last_commit_id"] == "sha-main-001"
    assert queue_service.messages == [
        {
            "review_record_id": body["review_record_id"],
            "platform_type": "gitlab",
            "attempt": 1,
        }
    ]

    record = db_session.get(ReviewRecord, body["review_record_id"])
    assert record is not None
    assert record.project_id == project.id
    assert record.event_type == "push"
    assert record.review_status == "queued"
    assert record.branch == "main"
    assert record.last_commit_id == "sha-main-001"
    assert record.external_commit_sha == "sha-main-001"
    assert record.author == "root-admin"
    assert record.webhook_data["after"] == "sha-main-001"
    assert record.webhook_data["project"]["id"] == "3003"


def test_projects_api_rejects_manual_review_for_inactive_project(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = Project(
        name="Inactive Review Project",
        key="inactive-review-project",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/inactive-review-project",
        default_branch="main",
        is_active=False,
        review_enabled=True,
        settings={
            "language": "python",
            "owner": "qa-team",
            "external_project_id": "3100",
            "gitlab_project_path": "acme/inactive-review-project",
        },
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/manual-review"
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PROJECT_INACTIVE"
    assert body["message"] == "停用项目不能触发手动审查。"


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
        ("delete", "/api/v1/projects/999999", None),
        ("post", "/api/v1/projects/999999/manual-review", None),
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
