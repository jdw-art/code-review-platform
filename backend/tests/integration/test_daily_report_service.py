from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models import Project, ProjectTemplate, ReviewRecord
from app.services.daily_report_service import DailyReportService


class FakeDailyReportReporter:
    def __init__(self) -> None:
        self.last_rows: list[dict[str, object]] | None = None

    def generate_report(self, rows: list[dict[str, object]]) -> str:
        self.last_rows = rows
        return "### 代码提交日报\n\n- alice: feat: daily report"


class FakeDailyReportSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def send_env_fallback(
        self,
        *,
        content: str,
        title: str,
        project_name: str | None,
        url_slug: str | None,
        webhook_data: dict[str, object],
    ) -> None:
        self.messages.append(
            {
                "content": content,
                "title": title,
                "project_name": project_name,
                "url_slug": url_slug,
                "webhook_data": webhook_data,
            }
        )


def _seed_review_record(
    db_session,
    *,
    author: str,
    commit_messages: list[str],
    review_status: str,
    review_result: str = "looks good",
    updated_at: datetime | None = None,
) -> ReviewRecord:
    effective_updated_at = updated_at or datetime.now(UTC)
    unique_suffix = str(int(effective_updated_at.timestamp() * 1_000_000))
    template = ProjectTemplate(
        name=f"Daily Template {author}",
        code=f"daily-template-{author}-{len(commit_messages)}-{unique_suffix}",
        description="Template for daily report tests",
        file_extensions=[".py"],
        review_prompt_template="review daily report changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name=f"Daily Project {author}",
        key=f"daily-project-{author}-{len(commit_messages)}-{review_status}-{unique_suffix}",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/group/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={},
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)

    record = ReviewRecord(
        project_id=project.id,
        event_type="merge_request",
        platform_type="gitlab",
        external_event_id=f"daily:{author}:{len(commit_messages)}:{review_status}:{unique_suffix}",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author=author,
        title="feat: daily report",
        source_branch="feature/daily",
        target_branch="main",
        commit_count=len(commit_messages),
        commit_messages=commit_messages,
        review_status=review_status,
        delivery_status="delivered",
        review_result=review_result,
        updated_at=effective_updated_at,
        webhook_data={},
        extra_data={},
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def test_daily_report_service_deduplicates_by_author_and_commit_messages(db_session) -> None:
    now = datetime.now(UTC)
    _seed_review_record(
        db_session,
        author="alice",
        commit_messages=["feat: a"],
        review_status="reviewed",
        updated_at=now,
    )
    _seed_review_record(
        db_session,
        author="alice",
        commit_messages=["feat: a"],
        review_status="reviewed",
        updated_at=now + timedelta(minutes=1),
    )
    _seed_review_record(
        db_session,
        author="bob",
        commit_messages=["feat: b"],
        review_status="reviewed",
        updated_at=now,
    )
    _seed_review_record(
        db_session,
        author="charlie",
        commit_messages=["feat: old"],
        review_status="reviewed",
        updated_at=now - timedelta(days=1),
    )
    _seed_review_record(
        db_session,
        author="david",
        commit_messages=["feat: skipped"],
        review_status="skipped",
        updated_at=now,
    )

    service = DailyReportService(session=db_session)
    rows = service.collect_today_rows()

    assert len(rows) == 2
    assert [row["author"] for row in rows] == ["alice", "bob"]
    assert rows[0]["commit_messages"] == ["feat: a"]


def test_daily_report_service_sends_markdown_via_sender(db_session) -> None:
    sender = FakeDailyReportSender()
    reporter = FakeDailyReportReporter()
    _seed_review_record(
        db_session,
        author="alice",
        commit_messages=["feat: daily report"],
        review_status="reviewed",
        review_result="looks good",
    )

    service = DailyReportService(
        session=db_session,
        sender=sender,
        reporter=reporter,
    )
    service.send_today_report()

    assert reporter.last_rows is not None
    assert reporter.last_rows[0]["author"] == "alice"
    assert sender.messages[0]["title"] == "代码提交日报"
    assert sender.messages[0]["content"].startswith("### 代码提交日报")
    assert sender.messages[0]["project_name"] is None
