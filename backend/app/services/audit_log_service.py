from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User
from app.db.session import get_db
from app.schemas.audit_log import AuditActionContext, AuditLogQuery, AuditLogResponse
from app.schemas.pagination import PageResponse

SENSITIVE_REQUEST_FIELDS = {
    "password",
    "current_password",
    "new_password",
    "api_key",
    "secret",
    "token",
    "refresh_token",
}

SYSTEM_AUDIT_RESOURCE_TYPES = {"audit_log", "auth"}


def sanitize_request_payload(payload: Any) -> Any:
    """递归脱敏请求载荷中的敏感字段，避免审计日志落明文密钥。"""
    if isinstance(payload, BaseModel):
        return sanitize_request_payload(payload.model_dump(mode="json", exclude_unset=True))
    if isinstance(payload, dict):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            normalized_key = str(key).lower()
            if normalized_key in SENSITIVE_REQUEST_FIELDS or normalized_key.endswith("_token"):
                sanitized[str(key)] = "***"
            else:
                sanitized[str(key)] = sanitize_request_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_request_payload(item) for item in payload]
    return payload


class AuditLogService:
    """封装后台审计日志写入、列表与详情查询逻辑。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    def record_action(
        self,
        context: AuditActionContext,
        *,
        actor: User | None = None,
        commit: bool = False,
    ) -> AuditLogResponse:
        """写入一条审计日志，并确保请求载荷已脱敏。"""
        audit_log = AuditLog(
            user_id=actor.id if actor is not None else context.user_id,
            username_snapshot=actor.username if actor is not None else context.username,
            action=context.action,
            resource_type=context.resource_type,
            resource_id=context.resource_id,
            resource_name_snapshot=context.resource_name,
            request_path=context.request_path,
            request_method=context.request_method,
            request_payload=sanitize_request_payload(context.request_payload) or {},
            response_status=context.response_status,
            result=context.result,
            error_message=context.error_message,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
        )
        self.session.add(audit_log)
        # 参与外层业务事务时也先刷新服务端默认值，避免返回模型缺少主键或时间戳。
        self.session.flush()
        if commit:
            self.session.commit()
        self.session.refresh(audit_log)
        return self._to_response(audit_log)

    async def list_logs(self, query: AuditLogQuery) -> PageResponse[AuditLogResponse]:
        """分页查询审计日志列表。"""
        filters = []
        if query.action:
            filters.append(AuditLog.action == query.action)
        if query.resource_type:
            filters.append(AuditLog.resource_type == query.resource_type)
        if query.user_id is not None:
            filters.append(AuditLog.user_id == query.user_id)
        if query.result:
            filters.append(AuditLog.result == query.result)

        total_statement = select(func.count()).select_from(AuditLog)
        list_statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if filters:
            total_statement = total_statement.where(*filters)
            list_statement = list_statement.where(*filters)

        total = self.session.scalar(total_statement) or 0
        logs = self.session.scalars(
            list_statement.offset(query.offset).limit(query.page_size)
        ).all()
        return PageResponse.create(
            items=[self._to_response(log) for log in logs],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_log(self, audit_log_id: int) -> AuditLogResponse:
        """按 ID 查询单条审计日志。"""
        audit_log = self.session.scalar(
            select(AuditLog).where(AuditLog.id == audit_log_id)
        )
        if audit_log is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审计日志不存在。",
            )
        return self._to_response(audit_log)

    async def purge_business_logs(self, current_user: User, request: Request) -> int:
        """清理业务审计日志，但保留系统安全审计记录。"""
        delete_statement = delete(AuditLog).where(
            AuditLog.resource_type.not_in(SYSTEM_AUDIT_RESOURCE_TYPES)
        )
        purge_result = self.session.execute(delete_statement)
        purged_count = int(purge_result.rowcount or 0)
        self.record_action(
            actor=current_user,
            context=self.build_context(
                request=request,
                current_user=current_user,
                action="audit_log.purge",
                resource_type="audit_log",
                payload={"purged_count": purged_count},
                response_status=status.HTTP_202_ACCEPTED,
            ),
        )
        self.session.commit()
        return purged_count

    @staticmethod
    def build_context(
        *,
        request: Request,
        action: str,
        resource_type: str,
        current_user: User | None = None,
        username: str | None = None,
        resource_id: int | None = None,
        resource_name: str | None = None,
        payload: Any = None,
        response_status: int | None = None,
        result: str = "success",
        error_message: str | None = None,
    ) -> AuditActionContext:
        """从 FastAPI Request 和当前用户构造审计上下文。"""
        client_host = request.client.host if request.client is not None else None
        actor_name = username or (current_user.username if current_user is not None else None)
        return AuditActionContext(
            user_id=current_user.id if current_user is not None else None,
            username=actor_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            request_path=request.url.path,
            request_method=request.method,
            request_payload=sanitize_request_payload(payload or {}),
            response_status=response_status,
            result=result,
            error_message=error_message,
            ip_address=client_host,
            user_agent=request.headers.get("user-agent"),
        )

    @staticmethod
    def _to_response(audit_log: AuditLog) -> AuditLogResponse:
        """将审计日志 ORM 对象转换为接口响应。"""
        return AuditLogResponse(
            id=audit_log.id,
            user_id=audit_log.user_id,
            username_snapshot=audit_log.username_snapshot,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            resource_name_snapshot=audit_log.resource_name_snapshot,
            request_path=audit_log.request_path,
            request_method=audit_log.request_method,
            request_payload=sanitize_request_payload(audit_log.request_payload),
            response_status=audit_log.response_status,
            result=audit_log.result,
            error_message=audit_log.error_message,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            created_at=audit_log.created_at,
        )
