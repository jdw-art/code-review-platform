from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_template import (
    ProjectTemplateOptionResponse,
    ProjectTemplateSummary,
)
from app.schemas.pagination import PageQuery


class PlatformOptionResponse(BaseModel):
    """项目平台下拉选项。"""

    label: str
    value: str


class ProjectResponse(BaseModel):
    """项目接口统一响应模型。"""

    id: int
    name: str
    key: str
    platform_type: str
    repo_url: str | None = None
    default_branch: str
    description: str | None = None
    is_active: bool
    review_enabled: bool
    language: str | None = None
    owner: str | None = None
    score_average: float | None = None
    last_review_at: datetime | None = None
    template: ProjectTemplateSummary | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ProjectCreateRequest(BaseModel):
    """创建项目请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=100)
    platform_type: str = Field(min_length=1, max_length=50)
    repo_url: str | None = None
    default_branch: str = Field(min_length=1, max_length=100)
    description: str | None = None
    template_id: int | None = None
    review_enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    """更新项目请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=100)
    platform_type: str = Field(min_length=1, max_length=50)
    repo_url: str | None = None
    default_branch: str = Field(min_length=1, max_length=100)
    description: str | None = None
    template_id: int | None = None
    review_enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectListQuery(PageQuery):
    """项目分页查询参数。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    search: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=100)


class ProjectStatusUpdateRequest(BaseModel):
    """项目启停状态更新请求体。"""

    is_active: bool


class ProjectOptionsResponse(BaseModel):
    """项目管理页面初始化所需的表单选项。"""

    platform_types: list[PlatformOptionResponse] = Field(default_factory=list)
    template_options: list[ProjectTemplateOptionResponse] = Field(default_factory=list)


class ProjectManualReviewResponse(BaseModel):
    """项目手动触发审查响应。"""

    review_record_id: int
    status: str
    branch: str
    last_commit_id: str
