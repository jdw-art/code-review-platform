from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Project, ReviewCommit, ReviewRecord
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.review_record import MockReviewIngestRequest, ReviewIngestResponse

logger = logging.getLogger(__name__)


class ReviewIngestService:
    """处理 mock 审查事件导入与标准化写入。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def ingest_mock_event(
        self,
        request: MockReviewIngestRequest,
    ) -> ReviewIngestResponse:
        """导入单条 mock push / merge request 事件。"""
        project = self._resolve_project(request)
        self._ensure_project_active(project)

        existing = self._find_existing_record(project.id, request)
        if existing is not None:
            logger.info(
                "Mock review event deduplicated review_record_id=%s project_id=%s.",
                existing.id,
                project.id,
            )
            return self._to_ingest_response(existing, project.key, is_duplicate=True)

        payload = request.payload
        commits_payload = self._normalize_commits(payload.get("commits", []))
        template = project.template
        event_updated_at = self._to_datetime(payload.get("updated_at"))
        review_record = ReviewRecord(
            project_id=project.id,
            event_type=request.event_type,
            external_event_id=self._get_optional_text(payload.get("external_event_id")),
            project_name_snapshot=project.name,
            template_id_snapshot=template.id if template is not None else None,
            template_name_snapshot=template.name if template is not None else None,
            review_prompt_snapshot=(
                template.review_prompt_template if template is not None else None
            ),
            author=str(payload["author"]),
            title=self._get_optional_text(payload.get("title")),
            branch=self._get_optional_text(payload.get("branch")),
            source_branch=self._get_optional_text(payload.get("source_branch")),
            target_branch=self._get_optional_text(payload.get("target_branch")),
            commit_count=len(commits_payload),
            commit_messages=[
                self._get_commit_message(commit_payload)
                for commit_payload in commits_payload
                if self._get_commit_message(commit_payload) is not None
            ],
            score=self._to_optional_float(payload.get("score")),
            review_status=self._resolve_review_status(payload),
            review_result=self._get_optional_text(payload.get("review_result")),
            summary=self._get_optional_text(payload.get("summary")),
            url=self._get_optional_text(payload.get("url")),
            url_slug=self._get_optional_text(payload.get("url_slug")),
            last_commit_id=self._get_optional_text(payload.get("last_commit_id")),
            additions=self._to_optional_int(payload.get("additions")) or 0,
            deletions=self._to_optional_int(payload.get("deletions")) or 0,
            agent_trace=self._normalize_agent_trace(payload.get("agent_trace")),
            webhook_data=self._normalize_dict(payload.get("webhook_data")),
            extra_data=self._build_extra_data(payload),
            updated_at=event_updated_at or datetime.now(UTC),
        )
        self.session.add(review_record)
        self.session.flush()

        for index, commit_payload in enumerate(commits_payload):
            commit_id = self._get_optional_text(commit_payload.get("id")) or f"commit-{index}"
            self.session.add(
                ReviewCommit(
                    review_record_id=review_record.id,
                    commit_id=commit_id,
                    short_commit_id=commit_id[:8],
                    author=self._get_optional_text(commit_payload.get("author")),
                    message=self._get_optional_text(commit_payload.get("message")),
                    timestamp=self._to_datetime(commit_payload.get("timestamp")),
                    sequence=index,
                    payload=commit_payload,
                )
            )

        self.session.commit()
        self.session.refresh(review_record)
        logger.info(
            "Mock review event ingested review_record_id=%s project_id=%s event_type=%s.",
            review_record.id,
            project.id,
            request.event_type,
        )
        return self._to_ingest_response(review_record, project.key, is_duplicate=False)

    def _resolve_project(self, request: MockReviewIngestRequest) -> Project:
        """根据外层定位字段优先解析平台内项目。"""
        statement = select(Project).options(selectinload(Project.template))
        if request.project_id is not None:
            project = self.session.scalar(statement.where(Project.id == request.project_id))
            if project is not None:
                return project
        if request.project_key:
            project = self.session.scalar(statement.where(Project.key == request.project_key))
            if project is not None:
                return project

        project_name = self._get_optional_text(request.payload.get("project_name"))
        if project_name:
            matches = self.session.scalars(
                statement.where(
                    Project.name == project_name,
                    Project.is_active.is_(True),
                )
            ).all()
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise DomainConflictError(
                    code="PROJECT_AMBIGUOUS",
                    message="存在多个同名启用项目，无法根据项目名称自动导入。",
                )

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在。")

    def _ensure_project_active(self, project: Project) -> None:
        """阻止向停用项目写入审查记录。"""
        if not project.is_active:
            raise DomainConflictError(
                code="PROJECT_INACTIVE",
                message="停用项目不能接收 mock 审查事件。",
            )

    def _find_existing_record(
        self,
        project_id: int,
        request: MockReviewIngestRequest,
    ) -> ReviewRecord | None:
        """按 external_event_id 或降级唯一键查找已导入记录。"""
        payload = request.payload
        external_event_id = self._get_optional_text(payload.get("external_event_id"))
        if external_event_id:
            return self.session.scalar(
                select(ReviewRecord).where(
                    ReviewRecord.project_id == project_id,
                    ReviewRecord.external_event_id == external_event_id,
                )
            )

        url_slug = self._get_optional_text(payload.get("url_slug"))
        last_commit_id = self._get_optional_text(payload.get("last_commit_id"))
        if not url_slug or not last_commit_id:
            return None

        return self.session.scalar(
            select(ReviewRecord).where(
                and_(
                    ReviewRecord.project_id == project_id,
                    ReviewRecord.event_type == request.event_type,
                    ReviewRecord.url_slug == url_slug,
                    ReviewRecord.last_commit_id == last_commit_id,
                )
            )
        )

    @staticmethod
    def _normalize_commits(raw_commits: Any) -> list[dict[str, Any]]:
        """标准化 commit 数组为字典列表。"""
        if not isinstance(raw_commits, list):
            return []
        normalized: list[dict[str, Any]] = []
        for raw_commit in raw_commits:
            if isinstance(raw_commit, dict):
                normalized.append(raw_commit)
        return normalized

    @staticmethod
    def _resolve_review_status(payload: dict[str, Any]) -> str:
        """根据输入 payload 推断审查状态。"""
        raw_status = payload.get("review_status")
        if isinstance(raw_status, str) and raw_status.strip():
            return raw_status.strip()
        if payload.get("review_result") is not None or payload.get("score") is not None:
            return "reviewed"
        return "pending"

    @staticmethod
    def _normalize_agent_trace(raw_trace: Any) -> dict[str, Any]:
        """兼容字符串或字典形式的 agent trace。"""
        if isinstance(raw_trace, dict):
            return raw_trace
        if raw_trace in (None, "", []):
            return {}
        return {"raw": raw_trace}

    @staticmethod
    def _normalize_dict(raw_value: Any) -> dict[str, Any]:
        """确保 JSON 字段总是落为对象。"""
        return raw_value if isinstance(raw_value, dict) else {}

    @staticmethod
    def _build_extra_data(payload: dict[str, Any]) -> dict[str, Any]:
        """保留未直接映射到主表字段的扩展数据。"""
        excluded_keys = {
            "author",
            "title",
            "branch",
            "source_branch",
            "target_branch",
            "commits",
            "score",
            "review_status",
            "review_result",
            "summary",
            "url",
            "url_slug",
            "last_commit_id",
            "additions",
            "deletions",
            "external_event_id",
            "webhook_data",
            "agent_trace",
        }
        return {
            key: value
            for key, value in payload.items()
            if key not in excluded_keys
        }

    @staticmethod
    def _get_optional_text(value: Any) -> str | None:
        """将可选文本值规范化为空或字符串。"""
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        """将输入安全转换为浮点数。"""
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _to_optional_int(value: Any) -> int | None:
        """将输入安全转换为整数。"""
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        """兼容 epoch 秒级时间戳与 ISO 时间字符串。"""
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC)
        if isinstance(value, str):
            try:
                return datetime.fromtimestamp(float(value), tz=UTC)
            except ValueError:
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    return None
        return None

    def _to_ingest_response(
        self,
        review_record: ReviewRecord,
        project_key: str,
        *,
        is_duplicate: bool,
    ) -> ReviewIngestResponse:
        """将导入结果转换为接口响应。"""
        return ReviewIngestResponse(
            id=review_record.id,
            project_id=review_record.project_id,
            project_key=project_key,
            event_type=review_record.event_type,
            commit_count=review_record.commit_count,
            is_duplicate=is_duplicate,
            created_at=review_record.created_at,
        )

    @staticmethod
    def _get_commit_message(commit_payload: dict[str, Any]) -> str | None:
        """提取并清洗单条 commit message。"""
        message = commit_payload.get("message")
        if message is None:
            return None
        text_value = str(message).strip()
        return text_value or None
