from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy import select

from app.db.models import Project, ProjectTemplate, ReviewCommit, ReviewRecord, User
from app.security.passwords import hash_password
from app.services.review_execution_service import ReviewExecutionService


class FakeAdapter:
    def __init__(self) -> None:
        self.changes_by_record_id: dict[int, list[dict[str, object]]] = {}
        self.commits_by_record_id: dict[int, list[dict[str, object]]] = {}

    def register_changes(self, record_id: int, changes: Sequence[dict[str, object]]) -> None:
        self.changes_by_record_id[record_id] = list(changes)

    def register_commits(self, record_id: int, commits: Sequence[dict[str, object]]) -> None:
        self.commits_by_record_id[record_id] = list(commits)

    def fetch_changes(self, record: ReviewRecord) -> list[dict[str, object]]:
        return list(self.changes_by_record_id.get(record.id, []))

    def fetch_commits(self, record: ReviewRecord) -> list[dict[str, object]]:
        return list(self.commits_by_record_id.get(record.id, []))


class FakeAdapterRegistry:
    def __init__(self) -> None:
        self.adapters: dict[str, FakeAdapter] = {}

    def register(self, platform_type: str, adapter: FakeAdapter) -> None:
        self.adapters[platform_type] = adapter

    def get(self, platform_type: str) -> FakeAdapter:
        return self.adapters[platform_type]


class FakeReviewer:
    def __init__(self, review_text: str = "总结\n总分：95分") -> None:
        self.review_text = review_text
        self.calls: list[dict[str, object]] = []

    def review(
        self,
        record: ReviewRecord,
        changes: list[dict[str, object]],
        commits: list[dict[str, object]],
    ) -> str:
        self.calls.append(
            {
                "record_id": record.id,
                "changes": changes,
                "commits": commits,
            }
        )
        return self.review_text

    def parse_score(self, review_text: str) -> int:
        if "95" in review_text:
            return 95
        if "88" in review_text:
            return 88
        return 0


class ExplodingReviewer(FakeReviewer):
    def __init__(self, error_message: str) -> None:
        super().__init__()
        self.error_message = error_message

    def review(
        self,
        record: ReviewRecord,
        changes: list[dict[str, object]],
        commits: list[dict[str, object]],
    ) -> str:
        del record, changes, commits
        raise RuntimeError(self.error_message)


class FakeCommentService:
    def __init__(self) -> None:
        self.published: list[int] = []

    def publish(self, record: ReviewRecord, review_text: str) -> None:
        del review_text
        self.published.append(record.id)


class ExplodingCommentService(FakeCommentService):
    def publish(self, record: ReviewRecord, review_text: str) -> None:
        del record, review_text
        raise RuntimeError("comment boom")


class FakeNotificationService:
    def __init__(self) -> None:
        self.sent: list[int] = []

    def notify(self, record: ReviewRecord) -> None:
        self.sent.append(record.id)


def _create_project_with_template(db_session) -> Project:
    user = User(
        username="review-execution-admin",
        password_hash=hash_password("review-execution-password"),
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    template = ProjectTemplate(
        name="Python Review Template",
        code="python-review-template",
        description="Template for review execution tests",
        file_extensions=[".py"],
        review_prompt_template="review python changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Execution Demo Project",
        key="execution-demo-key",
        platform_type="gitlab",
        repo_url="https://example.com/execution-demo.git",
        default_branch="main",
        review_enabled=True,
        template=template,
        created_by=1,
    )
    db_session.add_all([user, template, project])
    db_session.commit()
    db_session.refresh(project)
    return project


def _create_queued_review_record(db_session, *, platform_type: str = "gitlab") -> ReviewRecord:
    project = _create_project_with_template(db_session)
    project.platform_type = platform_type
    db_session.commit()

    record = ReviewRecord(
        project_id=project.id,
        event_type="merge_request",
        platform_type=platform_type,
        external_event_id="evt-001",
        external_project_id="project-001",
        external_merge_request_id="mr-001",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author="alice",
        title="Add worker execution service",
        source_branch="feature/task-7",
        target_branch="main",
        review_status="queued",
        delivery_status="pending",
        webhook_data={},
        extra_data={},
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def fake_adapter_registry() -> FakeAdapterRegistry:
    registry = FakeAdapterRegistry()
    registry.register("gitlab", FakeAdapter())
    registry.register("github", FakeAdapter())
    return registry


@pytest.fixture
def fake_reviewer() -> FakeReviewer:
    return FakeReviewer()


@pytest.fixture
def fake_comment_service() -> FakeCommentService:
    return FakeCommentService()


@pytest.fixture
def fake_notification_service() -> FakeNotificationService:
    return FakeNotificationService()


def test_execution_service_marks_reviewed_after_success(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [
            {
                "new_path": "backend/app/services/review_execution_service.py",
                "diff": "+print('ok')",
                "additions": 3,
                "deletions": 1,
            }
        ],
    )
    adapter.register_commits(
        record.id,
        [
            {
                "id": "abc123456789",
                "message": "feat: add worker execution service",
                "author": "alice",
                "timestamp": "2026-05-31T08:00:00Z",
            }
        ],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "reviewed"
    assert record.delivery_status == "delivered"
    assert record.score == 95
    assert record.review_result == "总结\n总分：95分"
    assert record.reviewed_at is not None
    assert record.failed_at is None
    assert record.error_message is None
    assert record.retry_count == 0
    assert record.additions == 3
    assert record.deletions == 1
    assert record.commit_count == 1
    assert record.commit_messages == ["feat: add worker execution service"]
    assert record.agent_trace["attempt"] == 1
    assert record.agent_trace["status"] == "reviewed"
    assert fake_comment_service.published == [record.id]
    assert fake_notification_service.sent == [record.id]


def test_execution_service_marks_skipped_when_no_supported_files(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".py")
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [
            {
                "new_path": "README.md",
                "diff": "+docs",
                "additions": 1,
                "deletions": 0,
            }
        ],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "docs: update readme", "author": "alice"}],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "skipped"
    assert record.delivery_status == "pending"
    assert record.review_result == "关注的文件没有修改"
    assert record.score is None
    assert record.reviewed_at is None
    assert record.failed_at is None
    assert record.commit_count == 1
    assert record.commit_messages == ["docs: update readme"]
    assert record.agent_trace["attempt"] == 1
    assert record.agent_trace["status"] == "skipped"
    assert fake_reviewer.calls == []


def test_execution_service_marks_failed_after_exception(
    db_session,
    fake_adapter_registry,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [{"new_path": "app.py", "diff": "+print('boom')", "additions": 1, "deletions": 0}],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: trigger error", "author": "alice"}],
    )

    reviewer = ExplodingReviewer(error_message="boom")
    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    with pytest.raises(RuntimeError, match="boom"):
        service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "failed"
    assert record.delivery_status == "pending"
    assert record.retry_count == 1
    assert record.failed_at is not None
    assert record.reviewed_at is None
    assert record.error_message == "boom"
    assert record.agent_trace["attempt"] == 1
    assert record.agent_trace["last_error"] == "boom"


def test_execution_service_persists_commit_rows_without_sequence_conflicts(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [{"new_path": "worker.py", "diff": "+pass", "additions": 1, "deletions": 0}],
    )
    adapter.register_commits(
        record.id,
        [
            {"id": "abc123456789", "message": "feat: first", "author": "alice"},
            {"id": "def987654321", "message": "fix: second", "author": "alice"},
        ],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)
    service.execute(review_record_id=record.id, attempt=2)

    commits = db_session.scalars(
        select(ReviewCommit)
        .where(ReviewCommit.review_record_id == record.id)
        .order_by(ReviewCommit.sequence.asc())
    ).all()
    assert len(commits) == 2
    assert [commit.sequence for commit in commits] == [0, 1]
    assert [commit.commit_id for commit in commits] == ["abc123456789", "def987654321"]


def test_execution_service_keeps_reviewed_when_comment_delivery_fails(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [{"new_path": "worker.py", "diff": "+pass", "additions": 1, "deletions": 0}],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: first", "author": "alice"}],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=ExplodingCommentService(),
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "reviewed"
    assert record.delivery_status == "comment_failed"
    assert record.retry_count == 0
    assert record.reviewed_at is not None
    assert record.failed_at is None
    assert record.error_message is None
    assert record.agent_trace["delivery_failures"] == ["comment"]
    assert fake_notification_service.sent == [record.id]


def test_execution_service_clears_previous_review_state_before_failure(
    db_session,
    fake_adapter_registry,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    record.score = 88
    record.review_result = "old result"
    record.reviewed_at = ReviewExecutionService._to_datetime("2026-05-31T08:00:00Z")
    record.delivery_status = "delivered"
    record.commit_count = 2
    record.commit_messages = ["old message"]
    record.agent_trace = {
        "attempt": 1,
        "status": "reviewed",
        "last_error": "stale error",
        "delivery_failures": ["comment"],
    }
    db_session.commit()

    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [{"new_path": "app.py", "diff": "+print('boom')", "additions": 1, "deletions": 0}],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: trigger error", "author": "alice"}],
    )

    reviewer = ExplodingReviewer(error_message="boom")
    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    with pytest.raises(RuntimeError, match="boom"):
        service.execute(review_record_id=record.id, attempt=2)

    db_session.refresh(record)
    assert record.review_status == "failed"
    assert record.delivery_status == "pending"
    assert record.score is None
    assert record.review_result is None
    assert record.reviewed_at is None
    assert record.retry_count == 1
    assert record.error_message == "boom"
    assert record.commit_count == 1
    assert record.commit_messages == ["feat: trigger error"]
    assert record.agent_trace["attempt"] == 2
    assert record.agent_trace["status"] == "failed"
    assert "delivery_failures" not in record.agent_trace


def test_execution_service_marks_failed_when_commit_persistence_breaks(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [{"new_path": "worker.py", "diff": "+pass", "additions": 1, "deletions": 0}],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: first", "author": "alice"}],
    )

    original_commit = db_session.commit
    original_rollback = db_session.rollback
    commit_calls = {"count": 0}
    rollback_calls = {"count": 0}

    def wrapped_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 2:
            raise RuntimeError("commit boom")
        original_commit()

    def wrapped_rollback() -> None:
        rollback_calls["count"] += 1
        original_rollback()

    monkeypatch.setattr(db_session, "commit", wrapped_commit)
    monkeypatch.setattr(db_session, "rollback", wrapped_rollback)

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    with pytest.raises(RuntimeError, match="commit boom"):
        service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert rollback_calls["count"] == 1
    assert record.review_status == "failed"
    assert record.delivery_status == "pending"
    assert record.retry_count == 1
    assert record.error_message == "commit boom"
    assert record.score is None
    assert record.review_result is None
    assert record.reviewed_at is None
    assert record.agent_trace["status"] == "failed"


def test_execution_service_marks_failed_when_processing_commit_breaks(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")

    original_commit = db_session.commit
    original_rollback = db_session.rollback
    commit_calls = {"count": 0}
    rollback_calls = {"count": 0}

    def wrapped_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 1:
            raise RuntimeError("processing commit boom")
        original_commit()

    def wrapped_rollback() -> None:
        rollback_calls["count"] += 1
        original_rollback()

    monkeypatch.setattr(db_session, "commit", wrapped_commit)
    monkeypatch.setattr(db_session, "rollback", wrapped_rollback)

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    with pytest.raises(RuntimeError, match="processing commit boom"):
        service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert rollback_calls["count"] == 1
    assert record.review_status == "failed"
    assert record.delivery_status == "pending"
    assert record.retry_count == 1
    assert record.error_message == "processing commit boom"
    assert record.score is None
    assert record.review_result is None
    assert record.reviewed_at is None
    assert record.agent_trace["attempt"] == 1
    assert record.agent_trace["status"] == "failed"


def test_execution_service_filters_supported_extensions(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".py,.ts")
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    adapter = fake_adapter_registry.get("gitlab")
    adapter.register_changes(
        record.id,
        [
            {"new_path": "notes.md", "diff": "+docs", "additions": 10, "deletions": 0},
            {"new_path": "worker.ts", "diff": "+const a = 1", "additions": 4, "deletions": 1},
            {"new_path": "removed.py", "diff": "-print('gone')", "deleted_file": True},
        ],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: mixed files", "author": "alice"}],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    assert len(fake_reviewer.calls) == 1
    reviewed_changes = fake_reviewer.calls[0]["changes"]
    assert reviewed_changes == [
        {"new_path": "worker.ts", "diff": "+const a = 1", "additions": 4, "deletions": 1}
    ]


def test_execution_service_ignores_deleted_change_variants(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".py")
    record = _create_queued_review_record(db_session, platform_type="github")
    adapter = fake_adapter_registry.get("github")
    adapter.register_changes(
        record.id,
        [
            {
                "new_path": "deleted-by-status.py",
                "diff": "-print('gone')",
                "status": "deleted",
                "additions": 0,
                "deletions": 1,
            },
            {
                "new_path": "removed-by-status.py",
                "diff": "-print('gone')",
                "status": "removed",
                "additions": 0,
                "deletions": 1,
            },
            {
                "new_path": "deleted-by-diff.py",
                "diff": "@@ -1,1 +0,0 @@\n-print('gone')",
                "additions": 0,
                "deletions": 1,
            },
        ],
    )
    adapter.register_commits(
        record.id,
        [{"id": "abc123", "message": "chore: remove file", "author": "alice"}],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "skipped"
    assert record.review_result == "关注的文件没有修改"
    assert record.additions == 0
    assert record.deletions == 0
    assert fake_reviewer.calls == []
