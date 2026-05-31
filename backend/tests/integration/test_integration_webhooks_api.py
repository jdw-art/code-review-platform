from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import select

from app.db.models import Project, ProjectTemplate, ReviewRecord
from app.main import app
from app.services.review_queue_service import get_review_queue_service


class FakeReviewQueueService:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def enqueue(
        self,
        *,
        review_record_id: int,
        platform_type: str,
        attempt: int = 1,
    ) -> None:
        self.messages.append(
            {
                "review_record_id": review_record_id,
                "platform_type": platform_type,
                "attempt": attempt,
            }
        )

    async def remove_message(self, raw_message: str) -> bool:
        del raw_message
        if self.messages:
            self.messages.pop()
            return True
        return False


class FailingReviewQueueService(FakeReviewQueueService):
    async def enqueue(
        self,
        *,
        review_record_id: int,
        platform_type: str,
        attempt: int = 1,
    ) -> None:
        del review_record_id, platform_type, attempt
        raise RuntimeError("queue unavailable")


@pytest.fixture
def fake_review_queue_service() -> Generator[FakeReviewQueueService, None, None]:
    service = FakeReviewQueueService()
    app.dependency_overrides[get_review_queue_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_review_queue_service, None)


@pytest.fixture
def failing_review_queue_service() -> Generator[FailingReviewQueueService, None, None]:
    service = FailingReviewQueueService()
    app.dependency_overrides[get_review_queue_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_review_queue_service, None)


@pytest.fixture
def seeded_gitlab_project(db_session) -> Project:
    template = ProjectTemplate(
        name="GitLab Webhook Template",
        code="gitlab-webhook-template",
        description="Template for webhook api tests",
        file_extensions=[".py"],
        review_prompt_template="review webhook changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="GitLab Webhook Project",
        key="gitlab-webhook-project",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/group/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={
            "gitlab_project_path": "group/repo",
            "external_project_id": "100",
        },
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def seeded_github_project(db_session) -> Project:
    template = ProjectTemplate(
        name="GitHub Webhook Template",
        code="github-webhook-template",
        description="Template for github webhook api tests",
        file_extensions=[".py"],
        review_prompt_template="review github webhook changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="GitHub Webhook Project",
        key="github-webhook-project",
        platform_type="github",
        repo_url="https://github.example.com/acme/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={
            "external_repo_full_name": "acme/repo",
            "external_project_id": "200",
        },
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)
    return project


def test_gitlab_webhook_creates_queued_review_record(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-001"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"

    record = db_session.get(ReviewRecord, body["review_record_id"])
    assert record is not None
    assert record.project_id == seeded_gitlab_project.id
    assert record.event_type == "merge_request"
    assert record.platform_type == "gitlab"
    assert record.external_event_id == "event-001"
    assert record.external_project_id == "100"
    assert record.author == "alice"
    assert record.title == "feat: x"
    assert record.source_branch == "feature/x"
    assert record.target_branch == "main"
    assert record.project_name_snapshot == seeded_gitlab_project.name
    assert record.template_id_snapshot == seeded_gitlab_project.template_id
    assert record.template_name_snapshot == seeded_gitlab_project.template.name
    assert (
        record.review_prompt_snapshot
        == seeded_gitlab_project.template.review_prompt_template
    )
    assert record.last_commit_id == "abc123"
    assert record.url == seeded_gitlab_project.repo_url
    assert record.review_status == "queued"
    assert record.delivery_status == "pending"
    assert record.webhook_data["object_kind"] == "merge_request"
    assert (
        db_session.scalar(
            select(ReviewRecord).where(
                ReviewRecord.project_id == seeded_gitlab_project.id
            )
        )
        is not None
    )
    assert fake_review_queue_service.messages == [
        {
            "review_record_id": record.id,
            "platform_type": "gitlab",
            "attempt": 1,
        }
    ]


def test_gitlab_webhook_deduplicates_existing_queued_record(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    existing = ReviewRecord(
        project_id=seeded_gitlab_project.id,
        event_type="merge_request",
        platform_type="gitlab",
        external_event_id="event-duplicate",
        external_project_id="100",
        project_name_snapshot=seeded_gitlab_project.name,
        template_id_snapshot=seeded_gitlab_project.template_id,
        template_name_snapshot=seeded_gitlab_project.template.name,
        review_prompt_snapshot=seeded_gitlab_project.template.review_prompt_template,
        author="alice",
        title="feat: x",
        source_branch="feature/x",
        target_branch="main",
        review_status="queued",
        delivery_status="pending",
        last_commit_id="abc123",
        webhook_data={},
    )
    db_session.add(existing)
    db_session.commit()

    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-duplicate"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "update",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": existing.id,
        "status": "duplicate",
    }
    stored_records = db_session.scalars(
        select(ReviewRecord).where(ReviewRecord.project_id == seeded_gitlab_project.id)
    ).all()
    assert len(stored_records) == 1
    assert stored_records[0].id == existing.id
    assert stored_records[0].review_status == "queued"
    assert fake_review_queue_service.messages == []


def test_gitlab_webhook_returns_skipped_when_project_not_found(
    client,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        json={
            "object_kind": "push",
            "project": {
                "id": 999,
                "web_url": "https://gitlab.example.com/unknown/repo",
                "path_with_namespace": "unknown/repo",
            },
            "user_name": "nobody",
            "ref": "refs/heads/main",
            "checkout_sha": "deadbeef",
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []


def test_gitlab_webhook_skips_draft_merge_request(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-draft"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "draft": True,
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []
    assert db_session.scalars(select(ReviewRecord)).all() == []


def test_gitlab_webhook_skips_unprotected_target_branch_when_flag_enabled(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED", "1")

    seeded_gitlab_project.settings = {
        **seeded_gitlab_project.settings,
        "protected_branches": ["main"],
    }
    db_session.add(seeded_gitlab_project)
    db_session.commit()

    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-protected"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "release",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []
    assert db_session.scalars(select(ReviewRecord)).all() == []


def test_gitlab_webhook_skips_unsupported_merge_request_action(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-close"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "close",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []
    assert db_session.scalars(select(ReviewRecord)).all() == []


def test_gitlab_webhook_skips_invalid_merge_request_payload(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-invalid"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
            },
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []
    assert db_session.scalars(select(ReviewRecord)).all() == []


def test_gitlab_webhook_accepts_last_commit_id_fallback_shape(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-last-commit-fallback"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit_id": "fallback-abc123",
            },
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"

    record = db_session.get(ReviewRecord, body["review_record_id"])
    assert record is not None
    assert record.last_commit_id == "fallback-abc123"


def test_gitlab_webhook_returns_skipped_for_malformed_json(
    client,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        content='{"broken"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []


def test_github_webhook_creates_queued_review_record(
    client,
    db_session,
    seeded_github_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/github",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-001",
        },
        json={
            "action": "opened",
            "repository": {
                "id": 200,
                "html_url": "https://github.example.com/acme/repo",
                "full_name": "acme/repo",
            },
            "pull_request": {
                "title": "feat: github webhook",
                "draft": False,
                "head": {"ref": "feature/github", "sha": "def456"},
                "base": {"ref": "main"},
                "user": {"login": "octocat"},
            },
            "sender": {"login": "octocat"},
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"

    record = db_session.get(ReviewRecord, body["review_record_id"])
    assert record is not None
    assert record.project_id == seeded_github_project.id
    assert record.platform_type == "github"
    assert record.event_type == "pull_request"
    assert record.external_event_id == "delivery-001"
    assert record.external_project_id == "200"
    assert record.author == "octocat"
    assert record.source_branch == "feature/github"
    assert record.target_branch == "main"
    assert record.last_commit_id == "def456"
    assert fake_review_queue_service.messages == [
        {
            "review_record_id": record.id,
            "platform_type": "github",
            "attempt": 1,
        }
    ]


def test_github_webhook_returns_skipped_when_headers_are_invalid(
    client,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/github",
        json={
            "repository": {
                "id": 200,
                "html_url": "https://github.example.com/acme/repo",
                "full_name": "acme/repo",
            }
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []


def test_github_webhook_returns_skipped_for_unsupported_event(
    client,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/github",
        headers={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "delivery-ping",
        },
        json={
            "repository": {
                "id": 200,
                "html_url": "https://github.example.com/acme/repo",
                "full_name": "acme/repo",
            }
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "review_record_id": 0,
        "status": "skipped",
    }
    assert fake_review_queue_service.messages == []


def test_gitlab_webhook_rolls_back_record_when_enqueue_fails(
    client,
    db_session,
    seeded_gitlab_project,
    failing_review_queue_service,
) -> None:
    del failing_review_queue_service

    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        headers={"X-Gitlab-Event-UUID": "event-enqueue-fail"},
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"name": "alice"},
            "object_attributes": {
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )

    assert response.status_code == 503
    assert db_session.scalars(
        select(ReviewRecord).where(
            ReviewRecord.external_event_id == "event-enqueue-fail"
        )
    ).all() == []
