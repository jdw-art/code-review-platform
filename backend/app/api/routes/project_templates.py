from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.db.models import User
from app.schemas.pagination import PageQuery, PageResponse
from app.schemas.project_template import (
    ProjectTemplateCreateRequest,
    ProjectTemplateOptionsResponse,
    ProjectTemplateResponse,
    ProjectTemplateStatusUpdateRequest,
    ProjectTemplateUpdateRequest,
)
from app.security.deps import require_permission
from app.services.project_template_service import ProjectTemplateService


router = APIRouter(prefix="/project-templates", tags=["project-templates"])


@router.get(
    "",
    response_model=PageResponse[ProjectTemplateResponse],
    dependencies=[Depends(require_permission("project_template:read"))],
    summary="获取项目模板列表",
    description="分页返回项目模板列表、支持的文件扩展名和 Review 提示词配置状态。需要 `project_template:read` 权限。",
)
async def list_project_templates(
    query: PageQuery = Depends(),
    service: ProjectTemplateService = Depends(),
) -> PageResponse[ProjectTemplateResponse]:
    """查询项目模板分页列表。"""
    return await service.list_templates(query)


@router.get(
    "/options",
    response_model=ProjectTemplateOptionsResponse,
    dependencies=[Depends(require_permission("project_template:read"))],
    summary="获取项目模板选项",
    description="返回项目模板管理页面需要的扩展名建议与提示词元数据预设。需要 `project_template:read` 权限。",
)
async def get_project_template_options(
    service: ProjectTemplateService = Depends(),
) -> ProjectTemplateOptionsResponse:
    """返回项目模板页面初始化选项。"""
    return await service.get_options()


@router.get(
    "/{template_id}",
    response_model=ProjectTemplateResponse,
    dependencies=[Depends(require_permission("project_template:read"))],
    summary="获取项目模板详情",
    description="根据模板 ID 返回单个项目模板详情。需要 `project_template:read` 权限。",
)
async def get_project_template(
    template_id: int,
    service: ProjectTemplateService = Depends(),
) -> ProjectTemplateResponse:
    """查询单个项目模板详情。"""
    return await service.get_template(template_id)


@router.post(
    "",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目模板",
    description="创建新的项目模板，并记录扩展名、提示词模板和元数据。需要 `project_template:create` 权限。",
)
async def create_project_template(
    payload: ProjectTemplateCreateRequest,
    current_user: User = Depends(require_permission("project_template:create")),
    service: ProjectTemplateService = Depends(),
) -> ProjectTemplateResponse:
    """创建新的项目模板。"""
    return await service.create_template(current_user, payload)


@router.put(
    "/{template_id}",
    response_model=ProjectTemplateResponse,
    summary="更新项目模板",
    description="更新指定项目模板的名称、编码、扩展名和 Review 提示词配置。需要 `project_template:update` 权限。",
)
async def update_project_template(
    template_id: int,
    payload: ProjectTemplateUpdateRequest,
    current_user: User = Depends(require_permission("project_template:update")),
    service: ProjectTemplateService = Depends(),
) -> ProjectTemplateResponse:
    """更新指定项目模板。"""
    return await service.update_template(current_user, template_id, payload)


@router.patch(
    "/{template_id}/status",
    response_model=ProjectTemplateResponse,
    summary="修改项目模板启用状态",
    description="启用或停用指定项目模板。需要 `project_template:status` 权限。",
)
async def update_project_template_status(
    template_id: int,
    payload: ProjectTemplateStatusUpdateRequest,
    current_user: User = Depends(require_permission("project_template:status")),
    service: ProjectTemplateService = Depends(),
) -> ProjectTemplateResponse:
    """修改指定项目模板的启停状态。"""
    return await service.update_status(current_user, template_id, payload)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除项目模板",
    description="删除指定项目模板。系统模板或仍被项目引用的模板不允许删除。需要 `project_template:delete` 权限。",
)
async def delete_project_template(
    template_id: int,
    current_user: User = Depends(require_permission("project_template:delete")),
    service: ProjectTemplateService = Depends(),
) -> None:
    """删除指定项目模板。"""
    await service.delete_template(current_user, template_id)
