from __future__ import annotations

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Project, ReviewRecord
from app.db.session import get_db
from app.schemas.dashboard import DashboardOverviewResponse


class DashboardService:
    """提供管理后台仪表盘概览统计。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def get_overview(self) -> DashboardOverviewResponse:
        """返回项目与审查记录的概览统计。"""
        total_projects = self.session.scalar(select(func.count()).select_from(Project)) or 0
        active_projects = self.session.scalar(
            select(func.count()).select_from(Project).where(Project.is_active.is_(True))
        ) or 0
        total_review_records = self.session.scalar(
            select(func.count()).select_from(ReviewRecord)
        ) or 0
        average_score = self.session.scalar(select(func.avg(ReviewRecord.score)))
        return DashboardOverviewResponse(
            total_projects=total_projects,
            active_projects=active_projects,
            total_review_records=total_review_records,
            average_score=round(float(average_score), 2) if average_score is not None else None,
        )
