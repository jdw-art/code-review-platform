from __future__ import annotations

import anyio
from sqlalchemy import select

from app.db.models import Project, ProjectTemplate, ReviewCommit, ReviewRecord, User
from app.schemas.review_record import MockReviewIngestRequest
from app.security.passwords import hash_password
from app.services.review_ingest_service import ReviewIngestService


def _create_project_with_template(db_session) -> Project:
    user = User(
        username="review-ingest-admin",
        password_hash=hash_password("review-ingest-password"),
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    template = ProjectTemplate(
        name="Java Review Template",
        code="java-review-template",
        description="Template for review ingest tests",
        file_extensions=[".java"],
        review_prompt_template="review java changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Demo Project",
        key="demo-key",
        platform_type="gitlab",
        repo_url="https://example.com/demo.git",
        default_branch="main",
        review_enabled=True,
        template=template,
        created_by=1,
    )
    db_session.add_all([user, template, project])
    db_session.commit()
    db_session.refresh(project)
    return project


def test_mock_ingest_prefers_outer_project_locator(db_session) -> None:
    project = _create_project_with_template(db_session)
    service = ReviewIngestService(session=db_session)
    payload = MockReviewIngestRequest(
        event_type="merge_request",
        project_key=project.key,
        payload={
            "project_name": "stale-display-name",
            "author": "alice",
            "source_branch": "feature/demo",
            "target_branch": "main",
            "commits": [{"id": "abc123", "message": "feat: add api"}],
            "url_slug": "mr-1",
            "last_commit_id": "abc123",
            "review_result": "ok",
            "webhook_data": {},
            "updated_at": 1710000000,
        },
    )

    result = anyio.run(service.ingest_mock_event, payload)

    assert result.project_id == project.id
    assert result.project_key == "demo-key"

    stored = db_session.scalar(select(ReviewRecord).where(ReviewRecord.id == result.id))
    assert stored is not None
    assert stored.project_name_snapshot == "Demo Project"
    assert stored.template_name_snapshot == "Java Review Template"
    assert stored.author == "alice"
    assert stored.source_branch == "feature/demo"
    assert stored.target_branch == "main"
    assert stored.commit_count == 1
    assert stored.commit_messages == ["feat: add api"]
    assert stored.extra_data["updated_at"] == 1710000000


def test_mock_ingest_persists_review_record_and_commit_rows(db_session) -> None:
    project = _create_project_with_template(db_session)
    service = ReviewIngestService(session=db_session)
    payload = MockReviewIngestRequest(
        event_type="push",
        project_id=project.id,
        payload={
            "author": "bob",
            "branch": "feature/push-demo",
            "score": 88.5,
            "review_result": "looks good",
            "url": "https://example.com/reviews/push-1",
            "url_slug": "push-1",
            "additions": 23,
            "deletions": 7,
            "last_commit_id": "def456",
            "commits": [
                {"id": "def456", "message": "feat: add worker", "author": "bob"},
                {"id": "def457", "message": "fix: polish worker", "author": "bob"},
            ],
            "webhook_data": {"object_kind": "push"},
            "updated_at": 1710001111,
            "trace_id": "trace-001",
        },
    )

    result = anyio.run(service.ingest_mock_event, payload)

    stored = db_session.scalar(select(ReviewRecord).where(ReviewRecord.id == result.id))
    assert stored is not None
    assert stored.event_type == "push"
    assert stored.branch == "feature/push-demo"
    assert stored.score == 88.5
    assert stored.review_result == "looks good"
    assert stored.url_slug == "push-1"
    assert stored.last_commit_id == "def456"
    assert stored.additions == 23
    assert stored.deletions == 7
    assert stored.webhook_data == {"object_kind": "push"}
    assert stored.extra_data["updated_at"] == 1710001111
    assert stored.extra_data["trace_id"] == "trace-001"

    commits = db_session.scalars(
        select(ReviewCommit)
        .where(ReviewCommit.review_record_id == stored.id)
        .order_by(ReviewCommit.sequence.asc())
    ).all()
    assert len(commits) == 2
    assert commits[0].commit_id == "def456"
    assert commits[0].sequence == 0
    assert commits[0].message == "feat: add worker"
    assert commits[1].commit_id == "def457"
    assert commits[1].sequence == 1
    assert commits[1].message == "fix: polish worker"


def test_mock_ingest_deduplicates_by_fallback_key(db_session) -> None:
    project = _create_project_with_template(db_session)
    service = ReviewIngestService(session=db_session)
    payload = MockReviewIngestRequest(
        event_type="merge_request",
        project_id=project.id,
        payload={
            "author": "dedupe-user",
            "url_slug": "mr-dedupe",
            "last_commit_id": "dedupe-commit",
            "commits": [{"id": "dedupe-commit", "message": "feat: dedupe"}],
            "review_result": "ok",
            "updated_at": 1710003333,
        },
    )

    first_result = anyio.run(service.ingest_mock_event, payload)
    second_result = anyio.run(service.ingest_mock_event, payload)

    assert first_result.id == second_result.id
    assert first_result.is_duplicate is False
    assert second_result.is_duplicate is True
    stored_records = db_session.scalars(
        select(ReviewRecord).where(ReviewRecord.project_id == project.id)
    ).all()
    assert len(stored_records) == 1
