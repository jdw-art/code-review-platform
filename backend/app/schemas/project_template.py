from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectTemplateSummary(BaseModel):
    """项目响应中使用的模板摘要。"""

    id: int
    name: str
    code: str
    is_active: bool
    review_prompt_configured: bool


class ProjectTemplateOptionResponse(BaseModel):
    """项目绑定模板时使用的下拉选项。"""

    id: int
    name: str
    code: str
    description: str | None = None
    file_extensions: list[str] = Field(default_factory=list)


class ProjectTemplateResponse(BaseModel):
    """项目模板接口统一响应模型。"""

    id: int
    name: str
    code: str
    description: str | None = None
    file_extensions: list[str] = Field(default_factory=list)
    review_prompt_template: str | None = None
    review_prompt_configured: bool
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    is_system: bool
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ProjectTemplateCreateRequest(BaseModel):
    """创建项目模板请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    file_extensions: list[str] = Field(min_length=1)
    review_prompt_template: str | None = None
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectTemplateUpdateRequest(BaseModel):
    """更新项目模板请求体。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    file_extensions: list[str] = Field(min_length=1)
    review_prompt_template: str | None = None
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectTemplateStatusUpdateRequest(BaseModel):
    """项目模板启停状态更新请求体。"""

    is_active: bool


class ProjectTemplateOptionsResponse(BaseModel):
    """项目模板管理页面初始化所需的表单选项。"""

    common_file_extensions: list[str] = Field(default_factory=list)
    prompt_metadata_presets: dict[str, list[str]] = Field(default_factory=dict)
