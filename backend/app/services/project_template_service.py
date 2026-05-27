from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Project, ProjectTemplate, User
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.pagination import PageQuery, PageResponse
from app.schemas.project_template import (
    ProjectTemplateCreateRequest,
    ProjectTemplateOptionResponse,
    ProjectTemplateOptionsResponse,
    ProjectTemplateResponse,
    ProjectTemplateStatusUpdateRequest,
    ProjectTemplateSummary,
    ProjectTemplateUpdateRequest,
)

logger = logging.getLogger(__name__)

COMMON_FILE_EXTENSIONS = [
    ".java",
    ".xml",
    ".yml",
    ".yaml",
    ".go",
    ".vue",
    ".ts",
    ".tsx",
    ".js",
    ".py",
    ".md",
]
PROMPT_METADATA_PRESETS = {
    "review_dimensions": ["correctness", "security", "performance", "maintainability"],
    "output_formats": ["markdown", "json"],
    "languages": ["zh-CN", "en-US"],
}


class ProjectTemplateService:
    """封装项目模板列表、详情、创建、更新与启停逻辑。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def list_templates(
        self,
        query: PageQuery,
    ) -> PageResponse[ProjectTemplateResponse]:
        """分页返回项目模板列表。"""
        total = self.session.scalar(select(func.count()).select_from(ProjectTemplate)) or 0
        templates = self.session.scalars(
            select(ProjectTemplate)
            .order_by(ProjectTemplate.id.asc())
            .offset(query.offset)
            .limit(query.page_size)
        ).all()
        return PageResponse.create(
            items=[self._to_template_response(template) for template in templates],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_template(self, template_id: int) -> ProjectTemplateResponse:
        """按模板 ID 查询详情。"""
        template = self._get_template_or_404(template_id)
        return self._to_template_response(template)

    async def create_template(
        self,
        current_user: User,
        payload: ProjectTemplateCreateRequest,
    ) -> ProjectTemplateResponse:
        """创建新的项目模板。"""
        self._ensure_unique_code(payload.code)
        template = ProjectTemplate(
            name=payload.name,
            code=payload.code,
            description=self._normalize_optional_text(payload.description),
            file_extensions=payload.file_extensions,
            review_prompt_template=self._normalize_optional_text(
                payload.review_prompt_template
            ),
            prompt_metadata=payload.prompt_metadata,
            is_system=False,
            is_active=payload.is_active,
            created_by=current_user.id,
        )
        self.session.add(template)
        self._commit_with_template_code_conflict_guard()
        self.session.refresh(template)
        logger.info("Project template created template_id=%s code=%s.", template.id, template.code)
        return self._to_template_response(template)

    async def update_template(
        self,
        current_user: User,
        template_id: int,
        payload: ProjectTemplateUpdateRequest,
    ) -> ProjectTemplateResponse:
        """更新指定项目模板。"""
        template = self._get_template_or_404(template_id)
        self._ensure_unique_code(payload.code, template_id=template.id)
        template.name = payload.name
        template.code = payload.code
        template.description = self._normalize_optional_text(payload.description)
        template.file_extensions = payload.file_extensions
        template.review_prompt_template = self._normalize_optional_text(
            payload.review_prompt_template
        )
        template.prompt_metadata = payload.prompt_metadata

        self._commit_with_template_code_conflict_guard()
        self.session.refresh(template)
        logger.info(
            "Project template updated template_id=%s by user_id=%s.",
            template.id,
            current_user.id,
        )
        return self._to_template_response(template)

    async def update_status(
        self,
        current_user: User,
        template_id: int,
        payload: ProjectTemplateStatusUpdateRequest,
    ) -> ProjectTemplateResponse:
        """更新项目模板启停状态。"""
        template = self._get_template_or_404(template_id)
        if not payload.is_active:
            self._ensure_template_can_be_disabled(template_id)
        template.is_active = payload.is_active

        self.session.commit()
        self.session.refresh(template)
        logger.info(
            "Project template status updated template_id=%s is_active=%s by user_id=%s.",
            template.id,
            template.is_active,
            current_user.id,
        )
        return self._to_template_response(template)

    async def get_options(self) -> ProjectTemplateOptionsResponse:
        """返回项目模板管理页面需要的静态选项。"""
        return ProjectTemplateOptionsResponse(
            common_file_extensions=COMMON_FILE_EXTENSIONS,
            prompt_metadata_presets=PROMPT_METADATA_PRESETS,
        )

    def _get_template_or_404(self, template_id: int) -> ProjectTemplate:
        """读取单个项目模板，不存在则抛出 404。"""
        template = self.session.scalar(
            select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        )
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目模板不存在。",
            )
        return template

    def _ensure_unique_code(self, code: str, template_id: int | None = None) -> None:
        """校验模板编码全局唯一。"""
        existing = self.session.scalar(
            select(ProjectTemplate).where(ProjectTemplate.code == code)
        )
        if existing is None:
            return
        if template_id is not None and existing.id == template_id:
            return
        raise DomainConflictError(
            code="PROJECT_TEMPLATE_CODE_ALREADY_EXISTS",
            message="项目模板编码已存在。",
        )

    def _ensure_template_can_be_disabled(self, template_id: int) -> None:
        """模板被启用项目绑定时，不允许直接停用。"""
        active_project_count = self.session.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.template_id == template_id,
                Project.is_active.is_(True),
            )
        ) or 0
        if active_project_count > 0:
            raise DomainConflictError(
                code="PROJECT_TEMPLATE_IN_USE",
                message="当前模板已被启用项目使用，解除绑定后才能停用。",
            )

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        """将空字符串折叠为 None，避免脏数据。"""
        if value is None:
            return None
        return value or None

    def _commit_with_template_code_conflict_guard(self) -> None:
        """将数据库唯一键冲突稳定转换为业务 409，避免并发写入时抛出 500。"""
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainConflictError(
                code="PROJECT_TEMPLATE_CODE_ALREADY_EXISTS",
                message="项目模板编码已存在。",
            ) from exc

    @staticmethod
    def to_template_summary(template: ProjectTemplate) -> ProjectTemplateSummary:
        """将模板 ORM 对象转换为项目响应使用的摘要。"""
        return ProjectTemplateSummary(
            id=template.id,
            name=template.name,
            code=template.code,
            is_active=template.is_active,
            review_prompt_configured=bool(
                template.review_prompt_template and template.review_prompt_template.strip()
            ),
        )

    @staticmethod
    def to_template_option(template: ProjectTemplate) -> ProjectTemplateOptionResponse:
        """将模板 ORM 对象转换为下拉选项。"""
        return ProjectTemplateOptionResponse(
            id=template.id,
            name=template.name,
            code=template.code,
            description=template.description,
            file_extensions=template.file_extensions,
        )

    @classmethod
    def _to_template_response(cls, template: ProjectTemplate) -> ProjectTemplateResponse:
        """将模板 ORM 对象转换为接口响应。"""
        summary = cls.to_template_summary(template)
        return ProjectTemplateResponse(
            id=template.id,
            name=template.name,
            code=template.code,
            description=template.description,
            file_extensions=template.file_extensions,
            review_prompt_template=template.review_prompt_template,
            review_prompt_configured=summary.review_prompt_configured,
            prompt_metadata=template.prompt_metadata,
            is_system=template.is_system,
            is_active=template.is_active,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
