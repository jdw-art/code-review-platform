from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.pagination import PageQuery


class ReviewRecordAuthorOption(BaseModel):
    """审查记录筛选面板使用的作者选项。"""

    label: str
    value: str


class ReviewRecordFiltersResponse(BaseModel):
    """审查记录列表筛选项响应。"""

    event_types: list[str] = Field(default_factory=list)
    authors: list[ReviewRecordAuthorOption] = Field(default_factory=list)


class ReviewCommitResponse(BaseModel):
    """审查记录详情中的 commit 明细。"""

    id: int
    commit_id: str
    short_commit_id: str | None = None
    author: str | None = None
    message: str | None = None
    timestamp: datetime | None = None
    sequence: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReviewRecordListItemResponse(BaseModel):
    """审查记录列表项响应。"""

    id: int
    project_id: int
    event_type: str
    external_event_id: str | None = None
    project_name_snapshot: str
    template_id_snapshot: int | None = None
    template_name_snapshot: str | None = None
    author: str
    title: str | None = None
    branch: str | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    commit_count: int
    commit_messages: list[str] = Field(default_factory=list)
    score: float | None = None
    review_status: str
    review_result: str | None = None
    summary: str | None = None
    url: str | None = None
    url_slug: str | None = None
    last_commit_id: str | None = None
    additions: int
    deletions: int
    created_at: datetime
    updated_at: datetime


class ReviewRecordDetailResponse(ReviewRecordListItemResponse):
    """审查记录详情响应。"""

    review_prompt_snapshot: str | None = None
    commits: list[ReviewCommitResponse] = Field(default_factory=list)


class ReviewRecordRawResponse(BaseModel):
    """审查记录原始载荷响应。"""

    id: int
    webhook_data: dict[str, Any] = Field(default_factory=dict)
    agent_trace: dict[str, Any] = Field(default_factory=dict)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class ReviewRecordQuery(PageQuery):
    """审查记录分页查询参数。"""

    project_id: int | None = None
    event_type: Literal["push", "merge_request"] | None = None
    author: str | None = Field(default=None, max_length=100)
    review_status: str | None = Field(default=None, max_length=32)


class MockReviewIngestRequest(BaseModel):
    """mock 审查事件导入请求。"""

    event_type: Literal["push", "merge_request"]
    project_id: int | None = None
    project_key: str | None = Field(default=None, max_length=100)
    source: str = Field(default="mock", max_length=50)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_project_locator(self) -> "MockReviewIngestRequest":
        """校验项目主定位字段至少提供一个。"""
        if self.project_id is None and not self.project_key:
            raise ValueError("project_id 与 project_key 至少提供一个。")
        return self


class ReviewIngestResponse(BaseModel):
    """mock 审查事件导入结果。"""

    id: int
    project_id: int
    project_key: str
    event_type: str
    commit_count: int
    is_duplicate: bool
    created_at: datetime
