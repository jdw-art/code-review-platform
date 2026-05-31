from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewRecord
from app.db.session import get_db
from app.review.reporting.daily_report_renderer import DailyReportRenderer
from app.services.review_notification_service import ReviewNotificationSender


@dataclass(slots=True)
class DailyReportRow:
    author: str
    commit_messages: list[str]
    review_result: str | None
    score: float | None
    project_name: str
    updated_at: datetime

    def to_payload(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "commit_messages": self.commit_messages,
            "review_result": self.review_result,
            "score": self.score,
            "project_name": self.project_name,
            "updated_at": int(self.updated_at.timestamp()),
        }
class DailyReportService:
    """基于 PostgreSQL 中的 review_records 生成并发送日报。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        sender: ReviewNotificationSender | None = None,
        reporter: Any | None = None,
    ) -> None:
        self.session = session
        self.sender = sender or ReviewNotificationSender()
        self.reporter = reporter

    def collect_today_rows(self) -> list[dict[str, Any]]:
        start_at, end_at = self._today_window()
        records = self.session.scalars(
            select(ReviewRecord)
            .where(
                ReviewRecord.review_status == "reviewed",
                ReviewRecord.updated_at >= start_at,
                ReviewRecord.updated_at <= end_at,
            )
            .order_by(ReviewRecord.author.asc(), ReviewRecord.updated_at.desc())
        ).all()

        deduplicated: dict[tuple[str, tuple[str, ...]], ReviewRecord] = {}
        for record in records:
            deduplicated[(record.author, tuple(record.commit_messages))] = record

        rows = [
            DailyReportRow(
                author=record.author,
                commit_messages=list(record.commit_messages),
                review_result=record.review_result,
                score=record.score,
                project_name=record.project_name_snapshot,
                updated_at=record.updated_at,
            ).to_payload()
            for record in deduplicated.values()
        ]
        rows.sort(key=lambda row: (str(row["author"]), -int(row["updated_at"])))
        return rows

    def send_today_report(self) -> str | None:
        rows = self.collect_today_rows()
        if not rows:
            return None

        reporter = self.reporter or DailyReportRenderer()
        report_content = reporter.generate_report(rows)
        self.sender.send_env_fallback(
            content=report_content,
            title="代码提交日报",
            project_name=None,
            url_slug=None,
            webhook_data={},
        )
        return report_content

    @staticmethod
    def _today_window() -> tuple[datetime, datetime]:
        now = datetime.now(UTC)
        start_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(days=1) - timedelta(microseconds=1)
        return start_at, end_at
