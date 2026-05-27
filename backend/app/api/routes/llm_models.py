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


router = APIRouter(prefix="/llm-models", tags=["llm-models"])


@router.get(
    "",
    response_model=PageResponse[LlmModelResponse],
    dependencies=[Depends(require_permission("llm_model:read"))],
    summary="获取大模型配置列表",
    description="分页返回大模型配置列表，响应中仅包含 API Key 掩码，不返回明文密钥。需要 `llm_model:read` 权限。",
)
async def list_llm_models(
    query: PageQuery = Depends(),
    service: LlmModelService = Depends(),
) -> PageResponse[LlmModelResponse]:
    """查询大模型配置分页列表。"""
    return await service.list_models(query)


@router.get(
    "/{model_id}",
    response_model=LlmModelResponse,
    dependencies=[Depends(require_permission("llm_model:read"))],
    summary="获取大模型配置详情",
    description="根据大模型配置 ID 返回详情，敏感 API Key 仅返回掩码。需要 `llm_model:read` 权限。",
)
async def get_llm_model(
    model_id: int,
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """查询单个大模型配置详情。"""
    return await service.get_model(model_id)


@router.post(
    "",
    response_model=LlmModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建大模型配置",
    description="创建新的大模型配置，并使用服务端密钥加密保存 API Key。需要 `llm_model:create` 权限。",
)
async def create_llm_model(
    request: Request,
    payload: LlmModelCreateRequest,
    current_user: User = Depends(require_permission("llm_model:create")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """创建新的大模型配置。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="create",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_model(current_user, payload, audit_context)


@router.put(
    "/{model_id}",
    response_model=LlmModelResponse,
    summary="更新大模型配置",
    description="更新指定大模型配置；传入新的 API Key 时会重新加密保存。需要 `llm_model:update` 权限。",
)
async def update_llm_model(
    request: Request,
    model_id: int,
    payload: LlmModelUpdateRequest,
    current_user: User = Depends(require_permission("llm_model:update")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """更新指定大模型配置。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="update",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_model(current_user, model_id, payload, audit_context)


@router.patch(
    "/{model_id}/status",
    response_model=LlmModelResponse,
    summary="修改大模型配置启用状态",
    description="启用或停用指定大模型配置。需要 `llm_model:status` 权限。",
)
async def update_llm_model_status(
    request: Request,
    model_id: int,
    payload: LlmModelStatusUpdateRequest,
    current_user: User = Depends(require_permission("llm_model:status")),
    service: LlmModelService = Depends(),
) -> LlmModelResponse:
    """修改指定大模型配置的启停状态。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="status",
        resource_type="llm_model",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_status(current_user, model_id, payload, audit_context)
