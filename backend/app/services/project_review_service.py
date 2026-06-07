from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.repository_provider import GitHubRepositoryProvider, GitLabRepositoryProvider
from app.db.models import Project, ReviewRecord, User
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.project import ProjectManualReviewResponse
from app.services.review_queue_service import ReviewQueueService, get_review_queue_service


class ProjectReviewService:
    """封装项目手动触发审查逻辑。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        queue_service: ReviewQueueService = Depends(get_review_queue_service),
    ) -> None:
        self.session = session
        self.queue_service = queue_service

    async def trigger_manual_review(
        self,
        current_user: User,
        project: Project | int,
    ) -> ProjectManualReviewResponse:
        if isinstance(project, int):
            project = self._get_project_or_404(project)
        self._ensure_manual_review_allowed(project)
        head_sha = self._resolve_default_branch_head(project)
        review_record = self._build_review_record(
            current_user=current_user,
            project=project,
            head_sha=head_sha,
        )
        self.session.add(review_record)
        self.session.flush()

        raw_message = await self.queue_service.enqueue(
            review_record_id=review_record.id,
            platform_type=project.platform_type,
        )
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            try:
                await self.queue_service.remove_message(raw_message)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="审查任务落库失败。",
            ) from exc

        self.session.refresh(review_record)
        return ProjectManualReviewResponse(
            review_record_id=review_record.id,
            status=review_record.review_status,
            branch=review_record.branch or project.default_branch,
            last_commit_id=review_record.last_commit_id or head_sha,
        )

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在。",
            )
        return project

    def _ensure_manual_review_allowed(self, project: Project) -> None:
        if not project.is_active:
            raise DomainConflictError(
                code="PROJECT_INACTIVE",
                message="停用项目不能触发手动审查。",
            )

        platform_type = project.platform_type.lower()
        if platform_type not in {"gitlab", "github"}:
            raise DomainConflictError(
                code="PROJECT_PLATFORM_UNSUPPORTED",
                message="当前项目平台暂不支持手动触发审查。",
            )

    def _build_review_record(
        self,
        *,
        current_user: User,
        project: Project,
        head_sha: str,
    ) -> ReviewRecord:
        project_name = project.name
        settings = project.settings if isinstance(project.settings, dict) else {}
        webhook_data = self._build_webhook_payload(project, head_sha, settings)
        template = project.template
        return ReviewRecord(
            project_id=project.id,
            event_type="push",
            platform_type=project.platform_type.lower(),
            external_event_id=f"manual:{project.id}:{head_sha}",
            external_project_id=self._optional_text(settings.get("external_project_id")),
            external_commit_sha=head_sha,
            project_name_snapshot=project_name,
            template_id_snapshot=template.id if template is not None else None,
            template_name_snapshot=template.name if template is not None else None,
            review_prompt_snapshot=(
                template.review_prompt_template if template is not None else None
            ),
            author=current_user.username,
            title=f"Manual review for {project.default_branch}",
            branch=project.default_branch,
            commit_count=0,
            commit_messages=[],
            review_status="queued",
            delivery_status="pending",
            url=project.repo_url,
            last_commit_id=head_sha,
            webhook_data=webhook_data,
            extra_data={
                "trigger_mode": "manual",
                "triggered_by": current_user.username,
                "triggered_at": self._now().isoformat(),
            },
            updated_at=self._now(),
        )

    def _build_webhook_payload(
        self,
        project: Project,
        head_sha: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        repo_url = project.repo_url
        platform_type = project.platform_type.lower()
        if platform_type == "gitlab":
            return {
                "object_kind": "push",
                "ref": f"refs/heads/{project.default_branch}",
                "before": self._zero_sha(),
                "after": head_sha,
                "checkout_sha": head_sha,
                "project_id": self._optional_text(settings.get("external_project_id")),
                "project": {
                    "id": self._optional_text(settings.get("external_project_id")),
                    "web_url": repo_url,
                    "path_with_namespace": self._optional_text(
                        settings.get("gitlab_project_path")
                    ),
                },
                "commits": [],
            }

        return {
            "ref": f"refs/heads/{project.default_branch}",
            "before": self._zero_sha(),
            "after": head_sha,
            "deleted": False,
            "repository": {
                "id": self._optional_text(settings.get("external_project_id")),
                "html_url": repo_url,
                "full_name": self._optional_text(settings.get("external_repo_full_name")),
            },
            "commits": [],
        }

    def _resolve_default_branch_head(self, project: Project) -> str:
        try:
            provider = self._build_repository_provider(project)
            return provider.resolve_branch_head(branch=project.default_branch)
        except DomainConflictError:
            raise
        except Exception as exc:  # pragma: no cover - exercised via API tests through monkeypatch
            raise DomainConflictError(
                code="PROJECT_HEAD_RESOLUTION_FAILED",
                message="无法读取仓库默认分支信息，请检查仓库接入配置。",
            ) from exc

    @staticmethod
    def _build_repository_provider(project: Project) -> Any:
        platform_type = project.platform_type.lower()
        if platform_type == "github":
            return GitHubRepositoryProvider(project=project)
        if platform_type == "gitlab":
            return GitLabRepositoryProvider(project=project)
        raise DomainConflictError(
            code="PROJECT_PLATFORM_UNSUPPORTED",
            message="当前项目平台暂不支持手动触发审查。",
        )

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _zero_sha() -> str:
        return "0" * 40

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
