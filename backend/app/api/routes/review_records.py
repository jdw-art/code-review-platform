from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.schemas.pagination import PageResponse
from app.schemas.review_record import (
    MockReviewIngestRequest,
    ReviewIngestResponse,
    ReviewRecordDetailResponse,
    ReviewRecordFiltersResponse,
    ReviewRecordListItemResponse,
    ReviewRecordQuery,
    ReviewRecordRawResponse,
)
from app.security.deps import require_permission
from app.services.review_ingest_service import ReviewIngestService
from app.services.review_record_service import ReviewRecordService


router = APIRouter(prefix="/review-records", tags=["review-records"])


@router.get(
    "",
    response_model=PageResponse[ReviewRecordListItemResponse],
    dependencies=[Depends(require_permission("review_record:read"))],
    summary="获取审查记录列表",
    description="分页返回项目审查记录，并支持按项目、事件类型、作者和审查状态筛选。需要 `review_record:read` 权限。",
)
async def list_review_records(
    query: ReviewRecordQuery = Depends(),
    service: ReviewRecordService = Depends(),
) -> PageResponse[ReviewRecordListItemResponse]:
    """查询审查记录分页列表。"""
    return await service.list_records(query)


@router.get(
    "/filters",
    response_model=ReviewRecordFiltersResponse,
    dependencies=[Depends(require_permission("review_record:read"))],
    summary="获取审查记录筛选项",
    description="返回审查记录列表页初始化所需的事件类型与作者筛选项。需要 `review_record:read` 权限。",
)
async def get_review_record_filters(
    service: ReviewRecordService = Depends(),
) -> ReviewRecordFiltersResponse:
    """返回审查记录筛选项。"""
    return await service.get_filters()


@router.get(
    "/{review_record_id}",
    response_model=ReviewRecordDetailResponse,
    dependencies=[Depends(require_permission("review_record:read"))],
    summary="获取审查记录详情",
    description="根据审查记录 ID 返回详情、commit 明细和模板快照。需要 `review_record:read` 权限。",
)
async def get_review_record(
    review_record_id: int,
    service: ReviewRecordService = Depends(),
) -> ReviewRecordDetailResponse:
    """查询单条审查记录详情。"""
    return await service.get_record(review_record_id)


@router.get(
    "/{review_record_id}/raw",
    response_model=ReviewRecordRawResponse,
    dependencies=[Depends(require_permission("review_record:raw"))],
    summary="获取审查记录原始数据",
    description="返回审查记录关联的原始 webhook 数据、agent trace 与扩展字段。需要 `review_record:raw` 权限。",
)
async def get_review_record_raw(
    review_record_id: int,
    service: ReviewRecordService = Depends(),
) -> ReviewRecordRawResponse:
    """查询单条审查记录的原始载荷。"""
    return await service.get_raw_record(review_record_id)


@router.post(
    "/mock-ingest",
    response_model=ReviewIngestResponse,
    dependencies=[Depends(require_permission("review_record:import"))],
    summary="导入模拟审查事件",
    description="接收双层结构的 mock 审查事件请求，并写入统一的审查记录与 commit 明细。需要 `review_record:import` 权限。",
)
async def ingest_mock_review(
    payload: MockReviewIngestRequest,
    response: Response,
    service: ReviewIngestService = Depends(),
) -> ReviewIngestResponse:
    """导入一条 mock push 或 merge request 事件。"""
    result = await service.ingest_mock_event(payload)
    response.status_code = (
        status.HTTP_200_OK if result.is_duplicate else status.HTTP_201_CREATED
    )
    return result
