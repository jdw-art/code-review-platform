from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Project, ReviewCommit, ReviewRecord
from app.db.session import get_db
from app.integrations.base import NormalizedWebhookEvent
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
            platform_type=project.platform_type,
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

    async def ingest_webhook_event(
        self,
        *,
        project: Project,
        event: NormalizedWebhookEvent,
    ) -> tuple[ReviewRecord, bool]:
        """写入真实 webhook 审查记录，重复事件直接返回既有记录。"""
        self._ensure_project_active(project)
        self._acquire_webhook_idempotency_lock(project.id, event)

        existing = self._find_existing_webhook_record(project.id, event)
        if existing is not None:
            if existing.review_status == "failed":
                existing.review_status = "queued"
                existing.failed_at = None
                existing.error_message = None
                self.session.flush()
                logger.info(
                    "Webhook review event re-queued review_record_id=%s project_id=%s platform=%s.",
                    existing.id,
                    project.id,
                    event.platform_type,
                )
                return existing, False
            logger.info(
                "Webhook review event deduplicated review_record_id=%s project_id=%s platform=%s.",
                existing.id,
                project.id,
                event.platform_type,
            )
            return existing, True

        template = project.template
        review_record = ReviewRecord(
            project_id=project.id,
            event_type=event.event_type,
            platform_type=event.platform_type,
            external_event_id=event.external_event_id,
            external_project_id=event.external_project_id,
            external_merge_request_id=self._extract_external_merge_request_id(event),
            external_pull_request_id=self._extract_external_pull_request_id(event),
            project_name_snapshot=project.name,
            template_id_snapshot=template.id if template is not None else None,
            template_name_snapshot=template.name if template is not None else None,
            review_prompt_snapshot=(
                template.review_prompt_template if template is not None else None
            ),
            author=event.author or "unknown",
            title=event.title,
            branch=event.branch,
            source_branch=event.source_branch,
            target_branch=event.target_branch,
            commit_count=0,
            commit_messages=[],
            review_status="queued",
            delivery_status="pending",
            url=event.repo_url,
            last_commit_id=event.last_commit_id,
            external_commit_sha=event.last_commit_id,
            webhook_data=event.webhook_data,
            updated_at=self._resolve_webhook_updated_at(event) or datetime.now(UTC),
        )
        self.session.add(review_record)
        self.session.flush()
        logger.info(
            "Webhook review event ingested review_record_id=%s project_id=%s platform=%s event_type=%s.",
            review_record.id,
            project.id,
            event.platform_type,
            event.event_type,
        )
        return review_record, False

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
                message="停用项目不能接收审查事件。",
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

    def _find_existing_webhook_record(
        self,
        project_id: int,
        event: NormalizedWebhookEvent,
    ) -> ReviewRecord | None:
        """按 webhook 唯一事件 ID 优先，缺失时退化为平台事件关键字段。"""
        if event.external_event_id:
            existing = self.session.scalar(
                select(ReviewRecord).where(
                    ReviewRecord.project_id == project_id,
                    ReviewRecord.external_event_id == event.external_event_id,
                )
            )
            if existing is not None:
                return existing

        external_merge_request_id = self._extract_external_merge_request_id(event)
        if event.event_type == "merge_request" and external_merge_request_id and event.last_commit_id:
            return self.session.scalar(
                select(ReviewRecord).where(
                    and_(
                        ReviewRecord.project_id == project_id,
                        ReviewRecord.event_type == event.event_type,
                        ReviewRecord.external_merge_request_id == external_merge_request_id,
                        ReviewRecord.last_commit_id == event.last_commit_id,
                    )
                )
            )

        external_pull_request_id = self._extract_external_pull_request_id(event)
        if event.event_type == "pull_request" and external_pull_request_id and event.last_commit_id:
            return self.session.scalar(
                select(ReviewRecord).where(
                    and_(
                        ReviewRecord.project_id == project_id,
                        ReviewRecord.event_type == event.event_type,
                        ReviewRecord.external_pull_request_id == external_pull_request_id,
                        ReviewRecord.last_commit_id == event.last_commit_id,
                    )
                )
            )

        if event.event_type == "push" and event.branch and event.last_commit_id:
            return self.session.scalar(
                select(ReviewRecord).where(
                    and_(
                        ReviewRecord.project_id == project_id,
                        ReviewRecord.event_type == event.event_type,
                        ReviewRecord.branch == event.branch,
                        ReviewRecord.last_commit_id == event.last_commit_id,
                    )
                )
            )

        if event.last_commit_id and (event.source_branch or event.target_branch):
            return self.session.scalar(
                select(ReviewRecord).where(
                    and_(
                        ReviewRecord.project_id == project_id,
                        ReviewRecord.event_type == event.event_type,
                        ReviewRecord.source_branch == event.source_branch,
                        ReviewRecord.target_branch == event.target_branch,
                        ReviewRecord.last_commit_id == event.last_commit_id,
                    )
                )
            )

        return None

    def _acquire_webhook_idempotency_lock(
        self,
        project_id: int,
        event: NormalizedWebhookEvent,
    ) -> None:
        lock_value = self._build_webhook_lock_value(project_id, event)
        self.session.execute(select(func.pg_advisory_xact_lock(lock_value)))

    def _build_webhook_lock_value(
        self,
        project_id: int,
        event: NormalizedWebhookEvent,
    ) -> int:
        token = self._build_webhook_dedupe_token(project_id, event)
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, byteorder="big", signed=False) & ((1 << 63) - 1)

    def _build_webhook_dedupe_token(
        self,
        project_id: int,
        event: NormalizedWebhookEvent,
    ) -> str:
        if event.external_event_id:
            return f"event:{project_id}:{event.external_event_id}"

        external_merge_request_id = self._extract_external_merge_request_id(event)
        if event.event_type == "merge_request" and external_merge_request_id and event.last_commit_id:
            return (
                f"merge_request:{project_id}:{external_merge_request_id}:"
                f"{event.last_commit_id}"
            )

        external_pull_request_id = self._extract_external_pull_request_id(event)
        if event.event_type == "pull_request" and external_pull_request_id and event.last_commit_id:
            return (
                f"pull_request:{project_id}:{external_pull_request_id}:"
                f"{event.last_commit_id}"
            )

        if event.event_type == "push" and event.branch and event.last_commit_id:
            return f"push:{project_id}:{event.branch}:{event.last_commit_id}"

        return (
            f"fallback:{project_id}:{event.event_type}:{event.source_branch or ''}:"
            f"{event.target_branch or ''}:{event.last_commit_id or ''}"
        )

    @staticmethod
    def _extract_external_merge_request_id(event: NormalizedWebhookEvent) -> str | None:
        if event.event_type != "merge_request":
            return None
        attributes = event.webhook_data.get("object_attributes")
        if not isinstance(attributes, dict):
            return None
        value = attributes.get("iid") or attributes.get("id")
        return str(value).strip() if value not in (None, "") else None

    @staticmethod
    def _extract_external_pull_request_id(event: NormalizedWebhookEvent) -> str | None:
        if event.event_type != "pull_request":
            return None
        pull_request = event.webhook_data.get("pull_request")
        if not isinstance(pull_request, dict):
            return None
        value = pull_request.get("number") or pull_request.get("id")
        return str(value).strip() if value not in (None, "") else None

    def _resolve_webhook_updated_at(self, event: NormalizedWebhookEvent) -> datetime | None:
        if event.event_type == "merge_request":
            attributes = event.webhook_data.get("object_attributes")
            if isinstance(attributes, dict):
                return self._to_datetime(attributes.get("updated_at"))
        if event.event_type == "pull_request":
            pull_request = event.webhook_data.get("pull_request")
            if isinstance(pull_request, dict):
                return self._to_datetime(pull_request.get("updated_at"))
        return None

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
