from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import RefreshSession, Role, User
from app.db.session import get_db
from app.schemas.common import DomainConflictError
from app.schemas.user import (
    UserCreateRequest,
    UserResetPasswordRequest,
    UserResponse,
    UserRoleSummary,
    UserStatusUpdateRequest,
    UserUpdateRequest,
    UserRoleAssignRequest,
)
from app.security.passwords import hash_password
from app.services.auth_service import RefreshSessionStore, get_refresh_session_store
from app.services.audit_log_service import AuditActionContext, AuditLogService

logger = logging.getLogger(__name__)


class UserService:
    """封装用户管理、状态变更、密码重置与角色分配逻辑。"""

    def __init__(
        self,
        session: Session = Depends(get_db),
        refresh_store: RefreshSessionStore = Depends(get_refresh_session_store),
        audit_log_service: AuditLogService = Depends(),
    ) -> None:
        self.session = session
        self.refresh_store = refresh_store
        self.audit_log_service = audit_log_service

    async def list_users(self) -> list[UserResponse]:
        """返回用户列表及其角色摘要。"""
        users = self.session.scalars(
            select(User)
            .options(selectinload(User.roles))
            .order_by(User.id.asc())
        ).all()
        return [self._to_user_response(user) for user in users]

    async def get_user(self, user_id: int) -> UserResponse:
        """按用户 ID 查询详情。"""
        user = self._get_user_or_404(user_id)
        return self._to_user_response(user)

    async def create_user(
        self,
        current_user: User,
        payload: UserCreateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> UserResponse:
        """创建新用户，并可选地绑定角色。"""
        if self.session.scalar(select(User).where(User.username == payload.username)) is not None:
            raise DomainConflictError(
                code="USERNAME_ALREADY_EXISTS",
                message="用户名已存在。",
            )

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            nickname=payload.nickname,
            email=payload.email,
            phone=payload.phone,
            is_active=True,
            is_superuser=payload.is_superuser,
            must_change_password=False,
        )
        if payload.role_ids:
            user.roles = self._get_roles_or_404(payload.role_ids)

        self.session.add(user)
        self.session.flush()
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_201_CREATED,
                ),
            )
        self.session.commit()
        self.session.refresh(user)
        user = self._get_user_or_404(user.id)
        logger.info("User created user_id=%s username=%s.", user.id, user.username)
        return self._to_user_response(user)

    async def update_user(
        self,
        current_user: User,
        user_id: int,
        payload: UserUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> UserResponse:
        """更新用户资料或超级管理员状态。"""
        user = self._get_user_or_404(user_id)
        updates = payload.model_dump(exclude_unset=True)
        if "is_superuser" in updates:
            # 降级超级管理员前，需要先校验是否触发自降权或最后一个超级管理员保护。
            self._ensure_superuser_change_allowed(
                current_user=current_user,
                target_user=user,
                next_is_superuser=bool(updates["is_superuser"]),
            )
        for field_name, field_value in updates.items():
            setattr(user, field_name, field_value)

        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(user)
        user = self._get_user_or_404(user.id)
        logger.info("User updated target_user_id=%s by user_id=%s.", user.id, current_user.id)
        return self._to_user_response(user)

    async def update_status(
        self,
        current_user: User,
        user_id: int,
        payload: UserStatusUpdateRequest,
        audit_context: AuditActionContext | None = None,
    ) -> UserResponse:
        """更新用户启用状态。"""
        user = self._get_user_or_404(user_id)
        if not payload.is_active:
            self._ensure_disable_allowed(current_user=current_user, target_user=user)
        user.is_active = payload.is_active
        if not payload.is_active:
            # 禁用用户后，应同步撤销其全部 refresh token 会话。
            self._mark_all_active_refresh_sessions_revoked(user.id)

        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(user)
        if not payload.is_active:
            try:
                await self.refresh_store.revoke_all_user_sessions(user.id)
            except Exception:
                logger.warning(
                    "Failed to revoke refresh sessions after disabling user_id=%s.",
                    user.id,
                    exc_info=True,
                )
        user = self._get_user_or_404(user.id)
        logger.info(
            "User status updated target_user_id=%s is_active=%s by user_id=%s.",
            user.id,
            user.is_active,
            current_user.id,
        )
        return self._to_user_response(user)

    async def reset_password(
        self,
        current_user: User,
        user_id: int,
        payload: UserResetPasswordRequest,
        audit_context: AuditActionContext | None = None,
    ) -> None:
        """重置指定用户密码并强制其下次登录修改密码。"""
        user = self._get_user_or_404(user_id)
        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = True
        self._mark_all_active_refresh_sessions_revoked(user.id)

        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_204_NO_CONTENT,
                ),
            )
        self.session.commit()
        try:
            await self.refresh_store.revoke_all_user_sessions(user.id)
        except Exception:
            logger.warning(
                "Failed to revoke refresh sessions after password reset for user_id=%s.",
                user.id,
                exc_info=True,
            )
        logger.info("Password reset for target_user_id=%s.", user.id)

    async def assign_roles(
        self,
        current_user: User,
        user_id: int,
        payload: UserRoleAssignRequest,
        audit_context: AuditActionContext | None = None,
    ) -> UserResponse:
        """覆盖指定用户当前的角色集合。"""
        user = self._get_user_or_404(user_id)
        user.roles = self._get_roles_or_404(payload.role_ids)

        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_200_OK,
                ),
            )
        self.session.commit()
        self.session.refresh(user)
        user = self._get_user_or_404(user.id)
        logger.info("Roles assigned to target_user_id=%s.", user.id)
        return self._to_user_response(user)

    async def delete_user(
        self,
        current_user: User,
        user_id: int,
        audit_context: AuditActionContext | None = None,
    ) -> None:
        """删除指定用户，并在提交后尽力撤销其 refresh token 会话。"""
        user = self._get_user_or_404(user_id)
        self._ensure_delete_allowed(current_user=current_user, target_user=user)

        deleted_user_id = user.id
        deleted_username = user.username
        if audit_context is not None:
            self.audit_log_service.record_action(
                actor=current_user,
                context=audit_context.with_resource(
                    resource_id=user.id,
                    resource_name=user.username,
                    response_status=status.HTTP_204_NO_CONTENT,
                ),
            )
        self.session.delete(user)
        self.session.commit()
        try:
            await self.refresh_store.revoke_all_user_sessions(deleted_user_id)
        except Exception:
            logger.warning(
                "Failed to revoke refresh sessions after deleting user_id=%s.",
                deleted_user_id,
                exc_info=True,
            )
        logger.info(
            "User deleted target_user_id=%s username=%s by user_id=%s.",
            deleted_user_id,
            deleted_username,
            current_user.id,
        )

    def _get_user_or_404(self, user_id: int) -> User:
        """读取单个用户，不存在则抛出 404。"""
        user = self.session.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    def _get_roles_or_404(self, role_ids: list[int]) -> list[Role]:
        """按 ID 列表读取角色集合，并校验全部存在。"""
        if not role_ids:
            return []

        roles = self.session.scalars(
            select(Role).where(Role.id.in_(role_ids)).order_by(Role.id.asc())
        ).all()
        if len(roles) != len(set(role_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found.",
            )
        return roles

    def _mark_all_active_refresh_sessions_revoked(self, user_id: int) -> None:
        """将用户全部未撤销的 refresh 会话标记为失效。"""
        active_sessions = self.session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
        ).all()
        revoked_at = datetime.now(UTC)
        for refresh_session in active_sessions:
            refresh_session.revoked_at = revoked_at

    def _ensure_disable_allowed(self, *, current_user: User, target_user: User) -> None:
        """校验当前禁用操作是否触发系统安全约束。"""
        if target_user.is_superuser and target_user.is_active and self._count_active_superusers() <= 1:
            raise DomainConflictError(
                code="LAST_SUPERUSER_DISABLE_FORBIDDEN",
                message="The last superuser cannot be disabled.",
            )
        if target_user.id == current_user.id:
            raise DomainConflictError(
                code="SELF_DISABLE_FORBIDDEN",
                message="You cannot disable your own account.",
            )

    def _ensure_superuser_change_allowed(
        self,
        *,
        current_user: User,
        target_user: User,
        next_is_superuser: bool,
    ) -> None:
        """校验超级管理员状态变更是否合法。"""
        if target_user.is_superuser and not next_is_superuser:
            if target_user.is_active and self._count_active_superusers() <= 1:
                raise DomainConflictError(
                    code="LAST_SUPERUSER_DEMOTE_FORBIDDEN",
                    message="The last superuser status cannot be removed.",
                )
            if target_user.id == current_user.id:
                raise DomainConflictError(
                    code="SELF_DEMOTE_FORBIDDEN",
                    message="You cannot remove your own superuser status.",
                )

    def _ensure_delete_allowed(self, *, current_user: User, target_user: User) -> None:
        """校验删除操作是否触发自删或最后超级管理员保护。"""
        if target_user.id == current_user.id:
            raise DomainConflictError(
                code="SELF_DELETE_FORBIDDEN",
                message="You cannot delete your own account.",
            )
        if target_user.is_superuser and target_user.is_active and self._count_active_superusers() <= 1:
            raise DomainConflictError(
                code="LAST_SUPERUSER_DELETE_FORBIDDEN",
                message="The last superuser cannot be deleted.",
            )

    def _count_active_superusers(self) -> int:
        """统计当前仍处于启用状态的超级管理员数量。"""
        return len(
            self.session.scalars(
                select(User.id).where(
                    User.is_superuser.is_(True),
                    User.is_active.is_(True),
                )
            ).all()
        )

    @staticmethod
    def _to_user_response(user: User) -> UserResponse:
        """将用户 ORM 对象转换为接口响应模型。"""
        return UserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            phone=user.phone,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            must_change_password=user.must_change_password,
            roles=[
                UserRoleSummary(id=role.id, name=role.name, code=role.code)
                for role in sorted(user.roles, key=lambda role: (role.name, role.id))
            ],
        )
