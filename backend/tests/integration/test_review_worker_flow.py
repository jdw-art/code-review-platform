from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fastapi import HTTPException

from app.db.models import Project, ProjectTemplate, ReviewRecord
from app.review.reviewer.protocol import ReviewRequest
from app.schemas.integration_webhook import ReviewQueueMessage
from app.services.review_execution_service import ReviewExecutionService
from app.workers.review_worker import run_single_review_job


class FakeQueueService:
    def __init__(self) -> None:
        self.messages: list[ReviewQueueMessage] = []

    def enqueue(
        self,
        *,
        review_record_id: int,
        platform_type: str,
        attempt: int = 1,
    ) -> None:
        self.messages.append(
            ReviewQueueMessage(
                review_record_id=review_record_id,
                platform_type=platform_type,
                attempt=attempt,
            )
        )

    def dequeue(self) -> ReviewQueueMessage | None:
        if not self.messages:
            return None
        return self.messages.pop(0)


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

    def publish_review_comment(self, *, record: ReviewRecord, review_result: str) -> None:
        del record, review_result


class FakeAdapterRegistry:
    def __init__(self) -> None:
        self.adapters: dict[str, FakeAdapter] = {}

    def register(self, platform_type: str, adapter: FakeAdapter) -> None:
        self.adapters[platform_type] = adapter

    def get(self, platform_type: str) -> FakeAdapter:
        return self.adapters[platform_type]


class FakeReviewer:
    def review(self, request: ReviewRequest) -> str:
        del request
        return "总结\n总分：95分"

    def parse_score(self, review_text: str) -> int:
        del review_text
        return 95


class FakeCommentService:
    def deliver(self, *, adapter: FakeAdapter, record: ReviewRecord, review_result: str) -> None:
        adapter.publish_review_comment(record=record, review_result=review_result)


class FakeNotificationService:
    def deliver(self, *, record: ReviewRecord) -> None:
        del record


def _create_queued_review_record(db_session) -> ReviewRecord:
    template = ProjectTemplate(
        name="Worker Template",
        code="worker-template",
        description="Template for worker flow tests",
        file_extensions=[".py"],
        review_prompt_template="review worker changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Worker Demo Project",
        key="worker-demo-project",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/group/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={"external_project_id": "100"},
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)

    record = ReviewRecord(
        project_id=project.id,
        event_type="merge_request",
        platform_type="gitlab",
        external_event_id="event-001",
        external_project_id="100",
        external_merge_request_id="7",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author="alice",
        title="feat: worker review",
        source_branch="feature/worker",
        target_branch="main",
        review_status="queued",
        delivery_status="pending",
        last_commit_id="abc123",
        webhook_data={},
        extra_data={},
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def test_review_worker_processes_queued_record_to_reviewed(
    db_session,
    monkeypatch,
) -> None:
    record = _create_queued_review_record(db_session)
    queue_service = FakeQueueService()
    queue_service.enqueue(
        review_record_id=record.id,
        platform_type="gitlab",
        attempt=1,
    )

    adapter_registry = FakeAdapterRegistry()
    adapter = FakeAdapter()
    adapter.register_changes(
        record.id,
        [
            {
                "new_path": "backend/app/workers/review_worker.py",
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
                "message": "feat: add review worker",
                "author": "alice",
                "timestamp": "2026-05-31T08:00:00Z",
            }
        ],
    )
    adapter_registry.register("gitlab", adapter)

    def fake_build_review_execution_service(*, session):
        return ReviewExecutionService(
            session=session,
            adapter_registry=adapter_registry,
            reviewer=FakeReviewer(),
            comment_service=FakeCommentService(),
            notification_service=FakeNotificationService(),
        )

    monkeypatch.setattr(
        "app.workers.review_worker.build_review_execution_service",
        fake_build_review_execution_service,
    )

    processed = run_single_review_job(queue_service, db_session)

    db_session.refresh(record)
    assert processed is True
    assert record.review_status == "reviewed"
    assert record.delivery_status == "delivered"
    assert record.score == 95


def test_review_worker_returns_false_when_queue_is_empty(db_session) -> None:
    del db_session
    assert run_single_review_job(FakeQueueService(), None) is False


def test_review_worker_skips_queue_messages_for_deleted_review_records(
    db_session,
    monkeypatch,
) -> None:
    queue_service = FakeQueueService()
    queue_service.enqueue(
        review_record_id=999,
        platform_type="gitlab",
        attempt=1,
    )

    def fake_build_review_execution_service(*, session):
        del session

        class MissingRecordService:
            def execute(self, *, review_record_id: int, attempt: int) -> None:
                del review_record_id, attempt
                raise HTTPException(status_code=404, detail="审查记录不存在。")

        return MissingRecordService()

    monkeypatch.setattr(
        "app.workers.review_worker.build_review_execution_service",
        fake_build_review_execution_service,
    )

    processed = run_single_review_job(queue_service, db_session)

    assert processed is True
    assert queue_service.messages == []


def test_review_worker_module_exposes_cli_entrypoint() -> None:
    worker_source = (
        Path(__file__).resolve().parents[2] / "app/workers/review_worker.py"
    ).read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in worker_source
