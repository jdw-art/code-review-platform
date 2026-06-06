from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.dashboard import DashboardOverviewResponse
from app.security.deps import require_permission
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    dependencies=[Depends(require_permission("dashboard:read"))],
    summary="获取仪表盘概览",
    description="返回高保真控制台所需的概览统计、最近审查、模型摘要与分析图表。需要 `dashboard:read` 权限。",
)
async def get_dashboard_overview(
    service: DashboardService = Depends(),
) -> DashboardOverviewResponse:
    """返回管理后台仪表盘概览统计。"""
    return await service.get_overview()
