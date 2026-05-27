from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.pagination import PageQuery


class MemberAnalyticsRecentReviewResponse(BaseModel):
    """成员分析详情中的最近审查记录摘要。"""

    review_record_id: int
    event_type: str
    title: str | None = None
    url_slug: str | None = None
    score: float | None = None
    review_status: str
    updated_at: datetime


class MemberAnalyticsListItemResponse(BaseModel):
    """成员分析列表项响应。"""

    project_member_id: int
    project_id: int
    project_name: str
    member_name: str
    member_email: str | None = None
    role_name: str | None = None
    review_count: int
    average_score: float | None = None
    total_additions: int
    total_deletions: int
    last_review_at: datetime | None = None


class MemberAnalyticsDetailResponse(MemberAnalyticsListItemResponse):
    """成员分析详情响应。"""

    recent_reviews: list[MemberAnalyticsRecentReviewResponse] = Field(default_factory=list)


class MemberAnalyticsQuery(PageQuery):
    """成员分析分页查询参数。"""

    project_id: int | None = None
