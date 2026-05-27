from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.db.models import User
from app.schemas.llm_model import (
    LlmModelCreateRequest,
    LlmModelResponse,
    LlmModelStatusUpdateRequest,
    LlmModelUpdateRequest,
)
from app.schemas.pagination import PageQuery, PageResponse
from app.security.deps import require_permission
from app.services.audit_log_service import AuditLogService
from app.services.llm_model_service import LlmModelService


router = APIRouter(prefix="/models", tags=["models"])


@router.get(
    "",
    response_model=PageResponse[LlmModelResponse],
    dependencies=[Depends(require_permission("llm_model:read"))],
    summary="获取模型列表",
    description="分页返回大模型配置列表，敏感 API Key 仅以掩码形式展示。需要 `llm_model:read` 权限。",
)
async def list_models(
    query: PageQuery = Depends(),
    service: LlmModelService = Depends(),
) -> PageResponse[LlmModelResponse]:
    """查询大模型配置分页列表。"""
    return await service.list_models(query)


@router.get(
    "/{model_id}",
    response_model=LlmModelResponse,
    dependencies=[Depends(require_permission("llm_model:read"))],
    summary="获取模型详情",
    description="根据模型 ID 返回单个大模型配置详情，敏感 API Key 不会明文返回。需要 `llm_model:read` 权限。",
)
async def get_model(
    model_id: int,
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """查询单个模型配置详情。"""
    return await service.get_model(model_id)


@router.post(
    "",
    response_model=LlmModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建模型配置",
    description="创建新的大模型配置，并对 API Key 做加密存储与掩码返回。需要 `llm_model:create` 权限。",
)
async def create_model(
    request: Request,
    payload: LlmModelCreateRequest,
    current_user: User = Depends(require_permission("llm_model:create")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """创建新的大模型配置。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="llm_model.create",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_model(current_user, payload, audit_context)


@router.put(
    "/{model_id}",
    response_model=LlmModelResponse,
    summary="更新模型配置",
    description="更新指定大模型配置的连接参数、提示词模板与默认状态。需要 `llm_model:update` 权限。",
)
async def update_model(
    request: Request,
    model_id: int,
    payload: LlmModelUpdateRequest,
    current_user: User = Depends(require_permission("llm_model:update")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """更新指定模型配置。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="llm_model.update",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_model(current_user, model_id, payload, audit_context)


@router.patch(
    "/{model_id}/status",
    response_model=LlmModelResponse,
    summary="修改模型启用状态",
    description="启用或停用指定大模型配置。需要 `llm_model:status` 权限。",
)
async def update_model_status(
    request: Request,
    model_id: int,
    payload: LlmModelStatusUpdateRequest,
    current_user: User = Depends(require_permission("llm_model:status")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """修改指定模型的启停状态。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="llm_model.status",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_status(current_user, model_id, payload, audit_context)
