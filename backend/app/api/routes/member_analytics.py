from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.member_analytics import (
    MemberAnalyticsDetailResponse,
    MemberAnalyticsListItemResponse,
    MemberAnalyticsQuery,
)
from app.schemas.pagination import PageResponse
from app.security.deps import require_permission
from app.services.member_analytics_service import MemberAnalyticsService


router = APIRouter(prefix="/member-analytics", tags=["member-analytics"])


@router.get(
    "",
    response_model=PageResponse[MemberAnalyticsListItemResponse],
    dependencies=[Depends(require_permission("member_analytics:read"))],
    summary="获取成员分析列表",
    description="分页返回项目成员的审查表现统计、评分均值与代码改动聚合结果。需要 `member_analytics:read` 权限。",
)
async def list_member_analytics(
    query: MemberAnalyticsQuery = Depends(),
    service: MemberAnalyticsService = Depends(),
) -> PageResponse[MemberAnalyticsListItemResponse]:
    """查询成员分析分页列表。"""
    return await service.list_member_analytics(query)


@router.get(
    "/{project_member_id}",
    response_model=MemberAnalyticsDetailResponse,
    dependencies=[Depends(require_permission("member_analytics:read"))],
    summary="获取成员分析详情",
    description="根据项目成员 ID 返回聚合统计与最近审查记录列表。需要 `member_analytics:read` 权限。",
)
async def get_member_analytics(
    project_member_id: int,
    service: MemberAnalyticsService = Depends(),
) -> MemberAnalyticsDetailResponse:
    """查询单个项目成员的分析详情。"""
    return await service.get_member_analytics(project_member_id)
