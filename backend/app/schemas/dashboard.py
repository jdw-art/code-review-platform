from __future__ import annotations

from pydantic import BaseModel


class DashboardOverviewResponse(BaseModel):
    """仪表盘概览统计响应。"""

    total_projects: int
    active_projects: int
    total_review_records: int
    average_score: float | None = None
