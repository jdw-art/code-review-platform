from __future__ import annotations

from sqlalchemy import Boolean, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin
from app.db.models.associations import role_menus, role_permissions, user_roles

SYSTEM_SUPER_ADMIN_ROLE_CODE = "super_admin"
SYSTEM_SUPER_ADMIN_ROLE_NAME = "Super Admin"


class Role(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )
    menus = relationship("Menu", secondary=role_menus, back_populates="roles")
