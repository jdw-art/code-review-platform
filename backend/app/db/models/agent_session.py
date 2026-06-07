from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentSession(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_agent_sessions_id_project_id"),
        Index("ix_agent_sessions_project_updated", "project_id", "updated_at"),
        Index("ix_agent_sessions_project_branch", "project_id", "branch"),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_head_sha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_workspace_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_runtime_identity_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    memory_state: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project")
    creator = relationship("User")
    messages = relationship(
        "AgentMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    runs = relationship(
        "AgentRun",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="AgentRun.session_id",
    )
    run_events = relationship(
        "AgentRunEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    artifacts = relationship(
        "AgentArtifact",
        back_populates="session",
        cascade="all, delete-orphan",
    )
