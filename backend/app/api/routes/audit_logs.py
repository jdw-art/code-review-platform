from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.db.models import User
from app.schemas.audit_log import AuditLogPurgeResponse, AuditLogQuery, AuditLogResponse
from app.schemas.pagination import PageResponse
from app.security.deps import require_permission
from app.services.audit_log_service import AuditLogService


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get(
    "",
    response_model=PageResponse[AuditLogResponse],
    dependencies=[Depends(require_permission("audit_log:read"))],
    summary="获取系统日志列表",
    description="分页返回后台操作审计日志，敏感字段以脱敏形式展示。需要 `audit_log:read` 权限。",
)
async def list_audit_logs(
    query: AuditLogQuery = Depends(),
    service: AuditLogService = Depends(),
) -> PageResponse[AuditLogResponse]:
    """查询后台操作审计日志分页列表。"""
    return await service.list_logs(query)


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    dependencies=[Depends(require_permission("audit_log:read"))],
    summary="获取系统日志详情",
    description="根据日志 ID 返回单条后台操作审计日志详情，敏感字段以脱敏形式展示。需要 `audit_log:read` 权限。",
)
async def get_audit_log(
    log_id: int,
    service: AuditLogService = Depends(),
) -> AuditLogResponse:
    """查询单条审计日志详情。"""
    return await service.get_log(log_id)


@router.post(
    "/purge",
    response_model=AuditLogPurgeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="清理业务审计日志",
    description="清理业务审计日志并保留系统安全日志。需要 `audit_log:purge` 权限。",
)
async def purge_audit_logs(
    request: Request,
    current_user: User = Depends(require_permission("audit_log:purge")),
    service: AuditLogService = Depends(),
) -> AuditLogPurgeResponse:
    """清理业务审计日志，并保留系统保底安全记录。"""
    purged_count = await service.purge_business_logs(current_user, request)
    return AuditLogPurgeResponse(purged_count=purged_count)
