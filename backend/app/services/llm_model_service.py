from __future__ import annotations

import logging
from typing import cast

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.models import LlmModel, User
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.llm_model import (
    LlmModelCreateRequest,
    LlmModelResponse,
    LlmModelStatusUpdateRequest,
    LlmModelUpdateRequest,
)
from app.schemas.pagination import PageQuery, PageResponse
from app.services.audit_log_service import AuditActionContext, AuditLogService
from app.services.auth_service import get_settings

logger = logging.getLogger(__name__)


def get_secret_cipher(settings: Settings = Depends(get_settings)) -> SecretCipher:
    """基于应用配置构造敏感字段加解密器。"""
    return SecretCipher(settings.secret_encryption_key)


def mask_secret(raw_secret: str | None) -> str | None:
    """对敏感密钥做固定长度掩码，响应中不暴露明文。"""
    if raw_secret is None or raw_secret == "":
        return None
    if len(raw_secret) <= 8:
        return "***"
    return f"{raw_secret[:4]}**********{raw_secret[-4:]}"


class LlmModelService:
    """封装大模型配置的列表、创建、更新与启停逻辑。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        cipher: SecretCipher = Depends(get_secret_cipher),
        audit_log_service: AuditLogService = Depends(),
    ) -> None:
        self.session = session
        self.cipher = cipher
        self.audit_log_service = audit_log_service

    async def list_models(self, query: PageQuery) -> PageResponse[LlmModelResponse]:
        """分页返回大模型配置列表。"""
        total = self.session.scalar(select(func.count()).select_from(LlmModel)) or 0
        models = self.session.scalars(
            select(LlmModel)
            .order_by(LlmModel.id.asc())
            .offset(query.offset)
            .limit(query.page_size)
        ).all()
        return PageResponse.create(
            items=[self._to_response(model) for model in models],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_model(self, model_id: int) -> LlmModelResponse:
        """按模型 ID 查询详情。"""
        model = self._get_model_or_404(model_id)
        return self._to_response(model)

    async def create_model(
        self,
        current_user: User,
        payload: LlmModelCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> LlmModelResponse:
        """创建新的大模型配置。"""
        if payload.is_default:
            self._ensure_default_available()
        model = LlmModel(
            name=payload.name,
            provider=payload.provider,
            model_code=payload.model_code,
            base_url=payload.base_url,
            api_key_encrypted=self._encrypt_optional_secret(payload.api_key),
            api_key_masked=mask_secret(payload.api_key),
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            prompt_template=payload.prompt_template,
            is_default=payload.is_default,
            is_active=payload.is_active,
        )
        self.session.add(model)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=model.id,
                    resource_name_snapshot=model.name,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self._commit_with_default_conflict_guard()
        self.session.refresh(model)
        logger.info("LLM model created model_id=%s model_code=%s.", model.id, model.model_code)
        return self._to_response(model)

    async def update_model(
        self,
        current_user: User,
        model_id: int,
        payload: LlmModelUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> LlmModelResponse:
        """更新指定大模型配置。"""
        model = self._get_model_or_404(model_id)
        if payload.is_default:
            self._ensure_default_available(exclude_model_id=model.id)
        model.name = payload.name
        model.provider = payload.provider
        model.model_code = payload.model_code
        model.base_url = payload.base_url
        if payload.api_key is not None:
            model.api_key_encrypted = self._encrypt_optional_secret(payload.api_key)
            model.api_key_masked = mask_secret(payload.api_key)
        model.temperature = payload.temperature
        model.max_tokens = payload.max_tokens
        model.top_p = payload.top_p
        model.prompt_template = payload.prompt_template
        model.is_default = payload.is_default
        model.is_active = payload.is_active
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=model.id,
                    resource_name_snapshot=model.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self._commit_with_default_conflict_guard()
        self.session.refresh(model)
        logger.info("LLM model updated model_id=%s by user_id=%s.", model.id, current_user.id)
        return self._to_response(model)

    async def update_status(
        self,
        current_user: User,
        model_id: int,
        payload: LlmModelStatusUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> LlmModelResponse:
        """更新大模型配置启停状态。"""
        model = self._get_model_or_404(model_id)
        model.is_active = payload.is_active
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=model.id,
                    resource_name_snapshot=model.name,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(model)
        logger.info(
            "LLM model status updated model_id=%s is_active=%s by user_id=%s.",
            model.id,
            model.is_active,
            current_user.id,
        )
        return self._to_response(model)

    def _get_model_or_404(self, model_id: int) -> LlmModel:
        """读取模型配置，不存在则抛出 404。"""
        model = self.session.scalar(select(LlmModel).where(LlmModel.id == model_id))
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型配置不存在。",
            )
        return model

    def _ensure_default_available(self, exclude_model_id: int | None = None) -> None:
        """校验默认模型唯一性，冲突时抛出稳定业务异常。"""
        statement = select(LlmModel).where(LlmModel.is_default.is_(True))
        if exclude_model_id is not None:
            statement = statement.where(LlmModel.id != exclude_model_id)
        existing = self.session.scalar(statement)
        if existing is not None:
            raise DomainConflictError(
                code="LLM_MODEL_DEFAULT_ALREADY_EXISTS",
                message="默认大模型配置已存在。",
            )

    def _commit_with_default_conflict_guard(self) -> None:
        """将唯一默认模型约束冲突稳定转换为业务 409。"""
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainConflictError(
                code="LLM_MODEL_DEFAULT_ALREADY_EXISTS",
                message="默认大模型配置已存在。",
            ) from exc

    def _encrypt_optional_secret(self, raw_secret: str | None) -> str | None:
        """对可选 API Key 做加密存储。"""
        if raw_secret is None or raw_secret == "":
            return None
        return self.cipher.encrypt_text(raw_secret)

    @staticmethod
    def _to_response(model: LlmModel) -> LlmModelResponse:
        """将大模型 ORM 对象转换为接口响应。"""
        return LlmModelResponse(
            id=model.id,
            name=model.name,
            provider=model.provider,
            model_code=model.model_code,
            base_url=model.base_url,
            api_key_masked=model.api_key_masked,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            top_p=model.top_p,
            prompt_template=model.prompt_template,
            is_default=model.is_default,
            is_active=model.is_active,
            last_test_status=model.last_test_status,
            last_test_message=model.last_test_message,
            last_test_at=model.last_test_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
