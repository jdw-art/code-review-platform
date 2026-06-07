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
    summary="获取机器人列表",
    description="分页返回通知机器人列表，敏感 Secret 仅以掩码形式展示。需要 `notification_bot:read` 权限。",
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
    summary="获取机器人详情",
    description="根据机器人 ID 返回单个通知机器人详情，敏感 Secret 不会明文返回。需要 `notification_bot:read` 权限。",
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
    description="创建新的通知机器人，并对 Secret 做加密存储与掩码返回。需要 `notification_bot:create` 权限。",
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
        action="notification_bot.create",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_201_CREATED,
    )
    return await service.create_bot(current_user, payload, audit_context)


@router.put(
    "/{bot_id}",
    response_model=NotificationBotResponse,
    summary="更新通知机器人",
    description="更新指定通知机器人的 webhook、密钥掩码与模板配置。需要 `notification_bot:update` 权限。",
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
        action="notification_bot.update",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_bot(current_user, bot_id, payload, audit_context)


@router.patch(
    "/{bot_id}/status",
    response_model=NotificationBotResponse,
    summary="修改机器人启用状态",
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
        action="notification_bot.status",
        resource_type="notification_bot",
        payload=payload,
        response_status=status.HTTP_200_OK,
    )
    return await service.update_status(current_user, bot_id, payload, audit_context)


@router.post(
    "/{bot_id}/test",
    response_model=NotificationBotResponse,
    summary="测试通知机器人",
    description="向指定通知机器人发送真实诊断消息，并回写最近测试结果。需要 `notification_bot:update` 权限。",
)
async def test_notification_bot(
    request: Request,
    bot_id: int,
    current_user: User = Depends(require_permission("notification_bot:update")),
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    """测试指定通知机器人并回写最近测试状态。"""
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="notification_bot.test",
        resource_type="notification_bot",
        response_status=status.HTTP_200_OK,
    )
    return await service.test_bot(current_user, bot_id, audit_context)
