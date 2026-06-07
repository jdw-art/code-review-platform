from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentRun(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("id", "session_id", name="uq_agent_runs_id_session_id"),
        ForeignKeyConstraint(
            ["session_id", "project_id"],
            ["agent_sessions.id", "agent_sessions.project_id"],
            name="fk_agent_runs_session_project",
            ondelete="CASCADE",
        ),
        Index("ix_agent_runs_session_created", "session_id", "created_at"),
        ForeignKeyConstraint(
            ["user_message_id", "session_id"],
            ["agent_messages.id", "agent_messages.session_id"],
            name="fk_agent_runs_user_message_session",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["assistant_message_id", "session_id"],
            ["agent_messages.id", "agent_messages.session_id"],
            name="fk_agent_runs_assistant_message_session",
            use_alter=True,
        ),
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "agent_messages.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_agent_runs_user_message_id",
        ),
        nullable=True,
    )
    assistant_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "agent_messages.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_agent_runs_assistant_message_id",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        server_default=text("'running'"),
    )
    stop_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_steps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_sha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    runtime_identity_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    completion_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    report_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("AgentSession", back_populates="runs", foreign_keys=[session_id])
    project = relationship("Project")
    messages = relationship(
        "AgentMessage",
        back_populates="run",
        foreign_keys="AgentMessage.run_id",
    )
    user_message = relationship(
        "AgentMessage",
        foreign_keys=[user_message_id],
        post_update=True,
    )
    assistant_message = relationship(
        "AgentMessage",
        foreign_keys=[assistant_message_id],
        post_update=True,
    )
    events = relationship(
        "AgentRunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        foreign_keys="AgentRunEvent.run_id",
    )
    artifacts = relationship(
        "AgentArtifact",
        back_populates="run",
        cascade="all, delete-orphan",
        foreign_keys="AgentArtifact.run_id",
    )
