from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ProjectMember(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    """项目成员关系表，用于成员分析与映射。"""

    __tablename__ = "project_members"
    __table_args__ = (
        Index("ix_project_members_project_id", "project_id"),
        Index(
            "ux_project_members_project_user",
            "project_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    member_name: Mapped[str] = mapped_column(String(100), nullable=False)
    member_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    project = relationship("Project", back_populates="members")
