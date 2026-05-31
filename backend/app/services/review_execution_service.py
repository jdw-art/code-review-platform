from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import ReviewCommit, ReviewRecord
from app.db.session import get_db
from app.review.reviewer.protocol import ReviewRequest
from app.services.review_comment_service import ReviewCommentService
from app.services.review_notification_service import ReviewNotificationService


class ReviewExecutionService:
    """Worker 主执行服务，负责编排单条审查记录的执行过程。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        *,
        adapter_registry: Any,
        reviewer: Any,
        comment_service: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self.session = session
        self.adapter_registry = adapter_registry
        self.reviewer = reviewer
        self.comment_service = comment_service or ReviewCommentService()
        self.notification_service = notification_service or ReviewNotificationService()

    def execute(self, *, review_record_id: int, attempt: int) -> None:
        record = self._get_record_or_raise(review_record_id)
        try:
            self._reset_execution_state(record)
            record.review_status = "processing"
            record.agent_trace = {
                "attempt": attempt,
                "started_at": self._now().isoformat(),
                "status": "processing",
            }
            self.session.commit()

            adapter = self.adapter_registry.get(record.platform_type)
            changes = adapter.fetch_changes(record)
            commits = adapter.fetch_commits(record)

            self._replace_commits(record.id, commits)
            self._update_commit_stats(record, commits)

            filtered_changes = self._filter_changes(changes)
            record.additions = sum(int(item.get("additions", 0) or 0) for item in filtered_changes)
            record.deletions = sum(int(item.get("deletions", 0) or 0) for item in filtered_changes)
            self.session.commit()

            if not filtered_changes:
                record.review_status = "skipped"
                record.review_result = "关注的文件没有修改"
                record.agent_trace = {
                    **self._normalize_trace(record.agent_trace),
                    "status": "skipped",
                    "finished_at": self._now().isoformat(),
                }
                self.session.commit()
                return

            review_text = self.reviewer.review(
                ReviewRequest(
                    record=record,
                    changes=filtered_changes,
                    commits=commits,
                )
            )
            record.score = self.reviewer.parse_score(review_text)
            record.review_result = review_text
            record.review_status = "reviewed"
            record.reviewed_at = self._now()
            record.failed_at = None
            record.error_message = None
            record.agent_trace = {
                **self._normalize_trace(record.agent_trace),
                "status": "reviewed",
                "finished_at": self._now().isoformat(),
                "change_count": len(filtered_changes),
                "commit_count": len(commits),
            }
            self.session.commit()

            self._deliver_review_result(record, review_text)
        except Exception as exc:
            self._mark_failed(record_id=review_record_id, attempt=attempt, error=exc)
            raise

    def _reset_execution_state(self, record: ReviewRecord) -> None:
        record.agent_trace = {}
        record.score = None
        record.review_result = None
        record.reviewed_at = None
        record.failed_at = None
        record.error_message = None
        record.delivery_status = "pending"
        record.commit_count = 0
        record.commit_messages = []
        record.additions = 0
        record.deletions = 0

    def _get_record_or_raise(self, review_record_id: int) -> ReviewRecord:
        record = self.session.get(ReviewRecord, review_record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审查记录不存在。",
            )
        return record

    def _replace_commits(self, review_record_id: int, commits: list[dict[str, Any]]) -> None:
        self.session.execute(
            delete(ReviewCommit).where(ReviewCommit.review_record_id == review_record_id)
        )
        self.session.flush()

        for index, commit_payload in enumerate(commits):
            commit_id = self._optional_text(commit_payload.get("id")) or f"commit-{index}"
            self.session.add(
                ReviewCommit(
                    review_record_id=review_record_id,
                    commit_id=commit_id,
                    short_commit_id=commit_id[:8],
                    author=self._optional_text(
                        commit_payload.get("author") or commit_payload.get("author_name")
                    ),
                    message=self._optional_text(commit_payload.get("message")),
                    timestamp=self._to_datetime(
                        commit_payload.get("timestamp") or commit_payload.get("created_at")
                    ),
                    sequence=index,
                    payload=dict(commit_payload),
                )
            )
        self.session.flush()

    def _update_commit_stats(self, record: ReviewRecord, commits: list[dict[str, Any]]) -> None:
        record.commit_count = len(commits)
        record.commit_messages = [
            message
            for message in (self._optional_text(item.get("message")) for item in commits)
            if message is not None
        ]

    def _deliver_review_result(self, record: ReviewRecord, review_text: str) -> None:
        delivery_failures: list[str] = []

        if self.comment_service is not None and hasattr(self.comment_service, "deliver"):
            try:
                self.comment_service.deliver(
                    adapter=self.adapter_registry.get(record.platform_type),
                    record=record,
                    review_result=review_text,
                )
            except Exception:
                delivery_failures.append("comment")

        if self.notification_service is not None and hasattr(self.notification_service, "deliver"):
            try:
                self.notification_service.deliver(record=record)
            except Exception:
                delivery_failures.append("notify")

        if not delivery_failures:
            record.delivery_status = "delivered"
        elif delivery_failures == ["comment"]:
            record.delivery_status = "comment_failed"
        elif delivery_failures == ["notify"]:
            record.delivery_status = "notify_failed"
        else:
            record.delivery_status = "partial_failed"

        if delivery_failures:
            record.agent_trace = {
                **self._normalize_trace(record.agent_trace),
                "delivery_failures": delivery_failures,
            }

        self.session.commit()

    def _mark_failed(self, *, record_id: int, attempt: int, error: Exception) -> None:
        self.session.rollback()
        record = self._get_record_or_raise(record_id)
        record.retry_count += 1
        record.review_status = "failed"
        record.score = None
        record.review_result = None
        record.reviewed_at = None
        record.failed_at = self._now()
        record.error_message = str(error)
        record.delivery_status = "pending"
        record.agent_trace = {
            "attempt": attempt,
            "status": "failed",
            "last_error": str(error),
            "finished_at": self._now().isoformat(),
        }
        self.session.commit()

    def _filter_changes(self, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        supported_extensions = [
            extension.strip()
            for extension in os.getenv("SUPPORTED_EXTENSIONS", ".java,.py,.php").split(",")
            if extension.strip()
        ]
        filtered_changes: list[dict[str, Any]] = []

        for change in changes:
            if self._is_deleted_change(change):
                continue

            new_path = self._optional_text(change.get("new_path"))
            if new_path is None:
                continue
            if supported_extensions and not any(new_path.endswith(ext) for ext in supported_extensions):
                continue

            filtered_changes.append(
                {
                    "new_path": new_path,
                    "diff": self._optional_text(change.get("diff")) or "",
                    "additions": int(change.get("additions", 0) or 0),
                    "deletions": int(change.get("deletions", 0) or 0),
                }
            )

        return filtered_changes

    @staticmethod
    def _is_deleted_change(change: dict[str, Any]) -> bool:
        if change.get("deleted_file"):
            return True

        status = change.get("status")
        if status in {"removed", "deleted"}:
            return True

        diff = change.get("diff")
        if not isinstance(diff, str) or not diff:
            return False
        lines = diff.splitlines()
        if not lines:
            return False
        if not lines[0].startswith("@@") or "+0,0 @@" not in lines[0]:
            return False
        return all(line.startswith("-") or line == "" for line in lines[1:])

    @staticmethod
    def _normalize_trace(trace: Any) -> dict[str, Any]:
        return dict(trace) if isinstance(trace, dict) else {}

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
