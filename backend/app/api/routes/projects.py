from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.db.models import User
from app.schemas.pagination import PageResponse
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectManualReviewResponse,
    ProjectOptionsResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
)
from app.security.deps import require_permission
from app.services.project_service import ProjectService
from app.services.project_review_service import ProjectReviewService


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    response_model=PageResponse[ProjectResponse],
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取项目列表",
    description="分页返回后台项目列表、模板绑定摘要与默认审查配置。需要 `project:read` 权限。",
)
async def list_projects(
    query: ProjectListQuery = Depends(),
    service: ProjectService = Depends(),
) -> PageResponse[ProjectResponse]:
    """查询项目分页列表。"""
    return await service.list_projects(query)


@router.get(
    "/options",
    response_model=ProjectOptionsResponse,
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取项目选项",
    description="返回项目管理页面需要的平台类型和可绑定模板选项。需要 `project:read` 权限。",
)
async def get_project_options(
    service: ProjectService = Depends(),
) -> ProjectOptionsResponse:
    """返回项目页面初始化选项。"""
    return await service.get_options()


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取项目详情",
    description="根据项目 ID 返回单个项目详情及其模板绑定摘要。需要 `project:read` 权限。",
)
async def get_project(
    project_id: int,
    service: ProjectService = Depends(),
) -> ProjectResponse:
    """查询单个项目详情。"""
    return await service.get_project(project_id)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目",
    description="创建新的后台管理项目，并可在创建时绑定启用中的项目模板。需要 `project:create` 权限。",
)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: User = Depends(require_permission("project:create")),
    service: ProjectService = Depends(),
) -> ProjectResponse:
    """创建新的项目。"""
    return await service.create_project(current_user, payload)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="更新项目",
    description="更新指定项目的基础信息、默认分支、模板绑定与审查配置。需要 `project:update` 权限。",
)
async def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: User = Depends(require_permission("project:update")),
    service: ProjectService = Depends(),
) -> ProjectResponse:
    """更新指定项目。"""
    return await service.update_project(current_user, project_id, payload)


@router.patch(
    "/{project_id}/status",
    response_model=ProjectResponse,
    summary="修改项目启用状态",
    description="启用或停用指定项目。需要 `project:status` 权限。",
)
async def update_project_status(
    project_id: int,
    payload: ProjectStatusUpdateRequest,
    current_user: User = Depends(require_permission("project:status")),
    service: ProjectService = Depends(),
) -> ProjectResponse:
    """修改指定项目的启停状态。"""
    return await service.update_status(current_user, project_id, payload)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除项目",
    description="删除指定项目及其关联的审查记录等级联数据。需要 `project:delete` 权限。",
)
async def delete_project(
    request: Request,
    project_id: int,
    current_user: User = Depends(require_permission("project:delete")),
    service: ProjectService = Depends(),
) -> Response:
    """删除指定项目。"""
    del request
    await service.delete_project(current_user, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/manual-review",
    response_model=ProjectManualReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发项目审查",
    description="按项目默认分支解析最新提交并创建真实 queued 审查记录。需要 `project:trigger-review` 权限。",
)
async def trigger_project_manual_review(
    request: Request,
    project_id: int,
    current_user: User = Depends(require_permission("project:trigger-review")),
    review_service: ProjectReviewService = Depends(),
) -> ProjectManualReviewResponse:
    """手动触发指定项目的默认分支审查。"""
    del request
    return await review_service.trigger_manual_review(current_user, project_id)
