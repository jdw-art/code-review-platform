from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Index, String, Text, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class Project(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    """项目主表，保存仓库接入与默认审查配置。"""

    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_key", "key", unique=True),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(50), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    review_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    template_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("project_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_model_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("llm_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_bot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("notification_bots.id", ondelete="SET NULL"),
        nullable=True,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
        doc="可存 external_repo_full_name、gitlab_project_path、external_project_id 等匹配信息",
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    template = relationship("ProjectTemplate", back_populates="projects")
    default_model = relationship("LlmModel", back_populates="projects")
    default_bot = relationship("NotificationBot", back_populates="projects")
    review_records = relationship(
        "ReviewRecord",
        back_populates="project",
        passive_deletes="all",
    )
    members = relationship(
        "ProjectMember",
        back_populates="project",
        passive_deletes="all",
    )
