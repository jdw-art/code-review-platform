from __future__ import annotations

from datetime import UTC, datetime
import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.crypto import SecretCipher
from app.db.models import NotificationBot, User
from app.db.session import get_db
from app.schemas.notification_bot import (
    NotificationBotCreateRequest,
    NotificationBotResponse,
    NotificationBotStatusUpdateRequest,
    NotificationBotUpdateRequest,
)
from app.schemas.pagination import PageQuery, PageResponse
from app.services.audit_log_service import AuditActionContext, AuditLogService
from app.services.llm_model_service import get_secret_cipher, mask_secret
from app.services.review_notification_service import ReviewNotificationSender, get_settings

logger = logging.getLogger(__name__)


def get_review_notification_sender(
    cipher: SecretCipher = Depends(get_secret_cipher),
) -> ReviewNotificationSender:
    return ReviewNotificationSender(settings=get_settings(), cipher=cipher)


class NotificationBotService:
    """封装通知机器人配置的列表、创建、更新与启停逻辑。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        cipher: SecretCipher = Depends(get_secret_cipher),
        audit_log_service: AuditLogService = Depends(),
        notification_sender: ReviewNotificationSender = Depends(get_review_notification_sender),
    ) -> None:
        self.session = session
        self.cipher = cipher
        self.audit_log_service = audit_log_service
        self.notification_sender = notification_sender

    async def list_bots(self, query: PageQuery) -> PageResponse[NotificationBotResponse]:
        """分页返回通知机器人列表。"""
        from sqlalchemy import func

        total = self.session.scalar(select(func.count()).select_from(NotificationBot)) or 0
        bots = self.session.scalars(
            select(NotificationBot)
            .order_by(NotificationBot.id.asc())
            .offset(query.offset)
            .limit(query.page_size)
        ).all()
        return PageResponse.create(
            items=[self._to_response(bot) for bot in bots],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_bot(self, bot_id: int) -> NotificationBotResponse:
        """按机器人 ID 查询详情。"""
        bot = self._get_bot_or_404(bot_id)
        return self._to_response(bot)

    async def create_bot(
        self,
        current_user: User,
        payload: NotificationBotCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> NotificationBotResponse:
        """创建新的通知机器人。"""
        bot = NotificationBot(
            name=payload.name,
            bot_type=payload.bot_type,
            webhook_url=payload.webhook_url,
            secret_encrypted=self._encrypt_optional_secret(payload.secret),
            secret_masked=mask_secret(payload.secret),
            mention_strategy=payload.mention_strategy,
            template_config=payload.template_config,
            is_active=payload.is_active,
        )
        self.session.add(bot)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=bot.id,
                    resource_name_snapshot=bot.name,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self.session.commit()
        self.session.refresh(bot)
        logger.info("Notification bot created bot_id=%s bot_type=%s.", bot.id, bot.bot_type)
        return self._to_response(bot)

    async def update_bot(
        self,
        current_user: User,
        bot_id: int,
        payload: NotificationBotUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> NotificationBotResponse:
        """更新指定通知机器人。"""
        bot = self._get_bot_or_404(bot_id)
        bot.name = payload.name
        bot.bot_type = payload.bot_type
        bot.webhook_url = payload.webhook_url
        if payload.secret is not None:
            bot.secret_encrypted = self._encrypt_optional_secret(payload.secret)
            bot.secret_masked = mask_secret(payload.secret)
        bot.mention_strategy = payload.mention_strategy
        bot.template_config = payload.template_config
        bot.is_active = payload.is_active
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=bot.id,
                    resource_name_snapshot=bot.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(bot)
        logger.info("Notification bot updated bot_id=%s by user_id=%s.", bot.id, current_user.id)
        return self._to_response(bot)

    async def update_status(
        self,
        current_user: User,
        bot_id: int,
        payload: NotificationBotStatusUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> NotificationBotResponse:
        """更新通知机器人启停状态。"""
        bot = self._get_bot_or_404(bot_id)
        bot.is_active = payload.is_active
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=bot.id,
                    resource_name_snapshot=bot.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(bot)
        logger.info(
            "Notification bot status updated bot_id=%s is_active=%s by user_id=%s.",
            bot.id,
            bot.is_active,
            current_user.id,
        )
        return self._to_response(bot)

    async def test_bot(
        self,
        current_user: User,
        bot_id: int,
        audit_context: AuditActionContext | None = None,
    ) -> NotificationBotResponse:
        """向指定机器人发送一条真实测试消息，并回写最近测试结果。"""
        bot = self._get_bot_or_404(bot_id)
        result = "success"
        error_message: str | None = None

        try:
            self.notification_sender.send(
                bot_type=bot.bot_type,
                webhook_url=bot.webhook_url,
                secret=self.notification_sender.resolve_bot_secret(bot),
                title=f"{bot.name} 诊断测试",
                content=(
                    "### 通知机器人诊断测试\n\n"
                    "这是一条由后台控制台发出的真实连通性检测消息，用于确认当前 Webhook 通道可用。"
                ),
                project_name=None,
                url_slug=None,
                webhook_data={},
            )
            bot.last_test_status = "success"
            bot.last_test_message = "测试消息发送成功。"
        except Exception as exc:
            result = "failure"
            error_message = str(exc) or "机器人测试失败。"
            bot.last_test_status = "failed"
            bot.last_test_message = error_message

        bot.last_test_at = datetime.now(UTC)
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=bot.id,
                    resource_name_snapshot=bot.name,
                    response_status=status.HTTP_200_OK,
                    result=result,
                    error_message=error_message,
                ),
            )
        self.session.commit()
        self.session.refresh(bot)
        logger.info(
            "Notification bot tested bot_id=%s status=%s by user_id=%s.",
            bot.id,
            bot.last_test_status,
            current_user.id,
        )
        return self._to_response(bot)

    def _get_bot_or_404(self, bot_id: int) -> NotificationBot:
        """读取机器人配置，不存在则抛出 404。"""
        bot = self.session.scalar(select(NotificationBot).where(NotificationBot.id == bot_id))
        if bot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="通知机器人不存在。",
            )
        return bot

    def _encrypt_optional_secret(self, raw_secret: str | None) -> str | None:
        """对可选机器人密钥做加密存储。"""
        if raw_secret is None or raw_secret == "":
            return None
        return self.cipher.encrypt_text(raw_secret)

    @staticmethod
    def _to_response(bot: NotificationBot) -> NotificationBotResponse:
        """将通知机器人 ORM 对象转换为接口响应。"""
        return NotificationBotResponse(
            id=bot.id,
            name=bot.name,
            bot_type=bot.bot_type,
            webhook_url=bot.webhook_url,
            secret_masked=bot.secret_masked,
            mention_strategy=bot.mention_strategy,
            template_config=bot.template_config,
            is_active=bot.is_active,
            last_test_status=bot.last_test_status,
            last_test_message=bot.last_test_message,
            last_test_at=bot.last_test_at,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
        )
