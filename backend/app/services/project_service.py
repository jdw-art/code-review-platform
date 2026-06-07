from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import Project, ProjectTemplate, ReviewRecord, User
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.pagination import PageResponse
from app.schemas.project import (
    PlatformOptionResponse,
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectOptionsResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
)
from app.services.project_template_service import ProjectTemplateService

logger = logging.getLogger(__name__)

PLATFORM_OPTIONS = [
    PlatformOptionResponse(label="GitLab", value="gitlab"),
    PlatformOptionResponse(label="GitHub", value="github"),
    PlatformOptionResponse(label="Gitea", value="gitea"),
    PlatformOptionResponse(label="Bitbucket", value="bitbucket"),
]


@dataclass(frozen=True)
class _ProjectReviewSummary:
    average_score: float | None
    last_review_at: datetime | None


class ProjectService:
    """封装项目列表、创建、更新、启停与表单选项逻辑。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def list_projects(self, query: ProjectListQuery) -> PageResponse[ProjectResponse]:
        """分页返回项目列表。"""
        filters = self._build_project_filters(query)
        total = self.session.scalar(
            select(func.count()).select_from(Project).where(*filters)
        ) or 0
        projects = self.session.scalars(
            select(Project)
            .options(selectinload(Project.template))
            .where(*filters)
            .order_by(Project.id.asc())
            .offset(query.offset)
            .limit(query.page_size)
        ).all()
        summaries = self._get_review_summaries([project.id for project in projects])
        return PageResponse.create(
            items=[
                self._to_project_response(
                    project,
                    review_summary=summaries.get(
                        project.id,
                        _ProjectReviewSummary(average_score=None, last_review_at=None),
                    ),
                )
                for project in projects
            ],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_project(self, project_id: int) -> ProjectResponse:
        """按项目 ID 查询详情。"""
        project = self._get_project_or_404(project_id)
        summary = self._get_review_summaries([project.id]).get(
            project.id,
            _ProjectReviewSummary(average_score=None, last_review_at=None),
        )
        return self._to_project_response(project, review_summary=summary)

    async def create_project(
        self,
        current_user: User,
        payload: ProjectCreateRequest,
    ) -> ProjectResponse:
        """创建新的项目。"""
        self._ensure_unique_key(payload.key)
        template = self._get_bindable_template(payload.template_id)
        project = Project(
            name=payload.name,
            key=payload.key,
            platform_type=payload.platform_type,
            repo_url=payload.repo_url,
            default_branch=payload.default_branch,
            description=payload.description,
            template_id=template.id if template is not None else None,
            review_enabled=payload.review_enabled,
            settings=self._normalize_project_settings(
                payload.settings,
                fallback_owner=current_user.username,
            ),
            created_by=current_user.id,
        )
        self.session.add(project)
        self._commit_with_project_key_conflict_guard()
        self.session.refresh(project)
        project = self._get_project_or_404(project.id)
        logger.info("Project created project_id=%s key=%s.", project.id, project.key)
        summary = self._get_review_summaries([project.id]).get(
            project.id,
            _ProjectReviewSummary(average_score=None, last_review_at=None),
        )
        return self._to_project_response(project, review_summary=summary)

    async def update_project(
        self,
        current_user: User,
        project_id: int,
        payload: ProjectUpdateRequest,
    ) -> ProjectResponse:
        """更新指定项目。"""
        project = self._get_project_or_404(project_id)
        self._ensure_unique_key(payload.key, project_id=project.id)
        template = self._get_bindable_template(payload.template_id)

        project.name = payload.name
        project.key = payload.key
        project.platform_type = payload.platform_type
        project.repo_url = payload.repo_url
        project.default_branch = payload.default_branch
        project.description = payload.description
        project.template_id = template.id if template is not None else None
        project.review_enabled = payload.review_enabled
        project.settings = self._normalize_project_settings(
            payload.settings,
            fallback_owner=current_user.username,
        )

        self._commit_with_project_key_conflict_guard()
        self.session.refresh(project)
        project = self._get_project_or_404(project.id)
        logger.info("Project updated project_id=%s by user_id=%s.", project.id, current_user.id)
        summary = self._get_review_summaries([project.id]).get(
            project.id,
            _ProjectReviewSummary(average_score=None, last_review_at=None),
        )
        return self._to_project_response(project, review_summary=summary)

    async def update_status(
        self,
        current_user: User,
        project_id: int,
        payload: ProjectStatusUpdateRequest,
    ) -> ProjectResponse:
        """更新项目启停状态。"""
        project = self._get_project_or_404(project_id)
        project.is_active = payload.is_active

        self.session.commit()
        self.session.refresh(project)
        project = self._get_project_or_404(project.id)
        logger.info(
            "Project status updated project_id=%s is_active=%s by user_id=%s.",
            project.id,
            project.is_active,
            current_user.id,
        )
        summary = self._get_review_summaries([project.id]).get(
            project.id,
            _ProjectReviewSummary(average_score=None, last_review_at=None),
        )
        return self._to_project_response(project, review_summary=summary)

    async def delete_project(
        self,
        current_user: User,
        project_id: int,
    ) -> None:
        """删除指定项目及其级联数据。"""
        project = self._get_project_or_404(project_id)
        self.session.delete(project)
        self.session.commit()
        logger.info("Project deleted project_id=%s by user_id=%s.", project_id, current_user.id)

    async def get_options(self) -> ProjectOptionsResponse:
        """返回项目管理页面所需的平台与模板选项。"""
        templates = self.session.scalars(
            select(ProjectTemplate)
            .where(ProjectTemplate.is_active.is_(True))
            .order_by(ProjectTemplate.id.asc())
        ).all()
        return ProjectOptionsResponse(
            platform_types=PLATFORM_OPTIONS,
            template_options=[
                ProjectTemplateService.to_template_option(template)
                for template in templates
            ],
        )

    def _get_project_or_404(self, project_id: int) -> Project:
        """读取单个项目，不存在则抛出 404。"""
        project = self.session.scalar(
            select(Project)
            .options(selectinload(Project.template))
            .where(Project.id == project_id)
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在。",
            )
        return project

    def _get_bindable_template(self, template_id: int | None) -> ProjectTemplate | None:
        """读取可绑定模板，并阻止绑定未启用模板。"""
        if template_id is None:
            return None

        template = self.session.scalar(
            select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        )
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目模板不存在。",
            )
        if not template.is_active:
            raise DomainConflictError(
                code="PROJECT_TEMPLATE_INACTIVE",
                message="项目模板未启用，不能绑定到项目。",
            )
        return template

    def _ensure_unique_key(self, key: str, project_id: int | None = None) -> None:
        """校验项目标识全局唯一。"""
        existing = self.session.scalar(select(Project).where(Project.key == key))
        if existing is None:
            return
        if project_id is not None and existing.id == project_id:
            return
        raise DomainConflictError(
            code="PROJECT_KEY_ALREADY_EXISTS",
            message="项目标识已存在。",
        )

    def _get_review_summaries(
        self,
        project_ids: list[int],
    ) -> dict[int, _ProjectReviewSummary]:
        if not project_ids:
            return {}

        rows = self.session.execute(
            select(
                ReviewRecord.project_id,
                func.avg(ReviewRecord.score).label("average_score"),
                func.max(ReviewRecord.created_at).label("last_review_at"),
            )
            .where(
                ReviewRecord.project_id.in_(project_ids),
                ReviewRecord.review_status == "reviewed",
                ReviewRecord.score.is_not(None),
            )
            .group_by(ReviewRecord.project_id)
        ).all()
        return {
            int(project_id): _ProjectReviewSummary(
                average_score=(
                    round(float(average_score), 2)
                    if average_score is not None
                    else None
                ),
                last_review_at=last_review_at,
            )
            for project_id, average_score, last_review_at in rows
        }

    def _commit_with_project_key_conflict_guard(self) -> None:
        """将数据库唯一键冲突稳定转换为业务 409，兜住并发写入场景。"""
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainConflictError(
                code="PROJECT_KEY_ALREADY_EXISTS",
                message="项目标识已存在。",
            ) from exc

    @staticmethod
    def _normalize_project_settings(
        settings: dict[str, object],
        *,
        fallback_owner: str,
    ) -> dict[str, object]:
        normalized: dict[str, object] = {
            key: value for key, value in settings.items() if value not in (None, "")
        }
        owner = str(normalized.get("owner") or "").strip()
        if owner:
            normalized["owner"] = owner
        else:
            normalized["owner"] = fallback_owner
        return normalized

    @staticmethod
    def _build_project_filters(query: ProjectListQuery) -> list[object]:
        filters: list[object] = []

        search = (query.search or "").strip()
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(Project.name).like(pattern),
                    func.lower(Project.key).like(pattern),
                    func.lower(func.coalesce(Project.repo_url, "")).like(pattern),
                    func.lower(func.coalesce(Project.description, "")).like(pattern),
                )
            )

        language = (query.language or "").strip()
        if language:
            filters.append(
                func.lower(
                    cast(Project.settings["language"].as_string(), String)
                )
                == language.lower()
            )

        return filters

    @staticmethod
    def _to_project_response(
        project: Project,
        *,
        review_summary: _ProjectReviewSummary,
    ) -> ProjectResponse:
        """将项目 ORM 对象转换为接口响应。"""
        template = (
            ProjectTemplateService.to_template_summary(project.template)
            if project.template is not None
            else None
        )
        settings = project.settings if isinstance(project.settings, dict) else {}
        return ProjectResponse(
            id=project.id,
            name=project.name,
            key=project.key,
            platform_type=project.platform_type,
            repo_url=project.repo_url,
            default_branch=project.default_branch,
            description=project.description,
            is_active=project.is_active,
            review_enabled=project.review_enabled,
            language=(
                str(settings.get("language")).strip()
                if settings.get("language") not in {None, ""}
                else None
            ),
            owner=(
                str(settings.get("owner")).strip()
                if settings.get("owner") not in {None, ""}
                else None
            ),
            score_average=review_summary.average_score,
            last_review_at=review_summary.last_review_at,
            template=template,
            settings=settings,
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
