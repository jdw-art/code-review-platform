from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.db.models import User
from app.schemas.notification_bot import (
    NotificationBotCreateRequest,
    NotificationBotResponse,
    NotificationBotStatusUpdateRequest,
    NotificationBotUpdateRequest,
)
from app.schemas.pagination import PageQuery, PageResponse
from app.security.deps import require_permission
from app.services.audit_log_service import AuditLogService
from app.services.notification_bot_service import NotificationBotService


router = APIRouter(prefix="/notification-bots", tags=["notification-bots"])


@router.get(
    "",
    response_model=PageResponse[NotificationBotResponse],
    dependencies=[Depends(require_permission("notification_bot:read"))],
    summary="获取通知机器人列表",
    description="分页返回通知机器人配置列表，响应中仅包含 Secret 掩码，不返回明文密钥。需要 `notification_bot:read` 权限。",
)
async def list_notification_bots(
    query: PageQuery = Depends(),
    service: NotificationBotService = Depends(),
) -> PageResponse[NotificationBotResponse]:
    """查询通知机器人分页列表。"""
    return await service.list_bots(query)


@router.get(
    "/{bot_id}",
    response_model=NotificationBotResponse,
    dependencies=[Depends(require_permission("notification_bot:read"))],
    summary="获取通知机器人详情",
    description="根据通知机器人 ID 返回详情，敏感 Secret 仅返回掩码。需要 `notification_bot:read` 权限。",
)
async def get_notification_bot(
    bot_id: int,
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    """查询单个通知机器人详情。"""
    return await service.get_bot(bot_id)


@router.post(
    "",
    response_model=NotificationBotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建通知机器人",
    description="创建新的通知机器人，并使用服务端密钥加密保存 Secret。需要 `notification_bot:create` 权限。",
)
async def create_notification_bot(
    request: Request,
    payload: NotificationBotCreateRequest,
    current_user: User = Depends(require_permission("notification_bot:create")),
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    """创建新的通知机器人。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="create",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_bot(current_user, payload, audit_context)


@router.put(
    "/{bot_id}",
    response_model=NotificationBotResponse,
    summary="更新通知机器人",
    description="更新指定通知机器人；传入新的 Secret 时会重新加密保存。需要 `notification_bot:update` 权限。",
)
async def update_notification_bot(
    request: Request,
    bot_id: int,
    payload: NotificationBotUpdateRequest,
    current_user: User = Depends(require_permission("notification_bot:update")),
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    """更新指定通知机器人。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="update",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_bot(current_user, bot_id, payload, audit_context)


@router.patch(
    "/{bot_id}/status",
    response_model=NotificationBotResponse,
    summary="修改通知机器人启用状态",
    description="启用或停用指定通知机器人。需要 `notification_bot:status` 权限。",
)
async def update_notification_bot_status(
    request: Request,
    bot_id: int,
    payload: NotificationBotStatusUpdateRequest,
    current_user: User = Depends(require_permission("notification_bot:status")),
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    """修改指定通知机器人的启停状态。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="status",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_status(current_user, bot_id, payload, audit_context)
