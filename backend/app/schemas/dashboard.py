from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardChartPoint(BaseModel):
    """项目或成员维度的图表聚合点。"""

    name: str
    commits: int
    avg_score: float | None = None
    additions: int
    deletions: int


class DashboardRecentReviewItem(BaseModel):
    """仪表盘最近审查记录。"""

    id: int
    project_name: str
    title: str | None = None
    branch: str | None = None
    commit_hash: str | None = None
    committer: str | None = None
    score: float | None = None
    review_status: str
    summary: str | None = None
    created_at: datetime


class DashboardModelSummary(BaseModel):
    """仪表盘展示的大模型摘要。"""

    id: int
    name: str
    provider: str
    temperature: float | None = None
    is_default: bool
    is_active: bool


class DashboardRepoHealthItem(BaseModel):
    """仓库健康摘要。"""

    project_id: int
    name: str
    is_active: bool
    review_count: int
    average_score: float | None = None
    last_review_at: datetime | None = None


class DashboardOverviewResponse(BaseModel):
    """仪表盘概览统计响应。"""

    total_projects: int
    active_projects: int
    total_review_records: int
    average_score: float | None = None
    active_model_name: str | None = None
    recent_reviews: list[DashboardRecentReviewItem] = Field(default_factory=list)
    project_chart: list[DashboardChartPoint] = Field(default_factory=list)
    member_chart: list[DashboardChartPoint] = Field(default_factory=list)
    models: list[DashboardModelSummary] = Field(default_factory=list)
    repo_health: list[DashboardRepoHealthItem] = Field(default_factory=list)
