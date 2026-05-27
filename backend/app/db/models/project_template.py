from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Index, String, Text, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ProjectTemplate(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    """项目模板主表，保存审查提示词模板配置。"""

    __tablename__ = "project_templates"
    __table_args__ = (Index("ix_project_templates_code", "code", unique=True),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_extensions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    review_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    projects = relationship("Project", back_populates="template")
