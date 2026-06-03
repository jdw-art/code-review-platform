from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentRun(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_session_created", "session_id", "created_at"),
        Index("ix_agent_runs_status", "status"),
        UniqueConstraint("id", "session_id", name="uq_agent_runs_id_session"),
        ForeignKeyConstraint(
            ["session_id", "project_id"],
            ["agent_sessions.id", "agent_sessions.project_id"],
            name="fk_agent_runs_session_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_message_id", "session_id"],
            ["agent_messages.id", "agent_messages.session_id"],
            name="fk_agent_runs_user_message",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["assistant_message_id", "session_id"],
            ["agent_messages.id", "agent_messages.session_id"],
            name="fk_agent_runs_assistant_message",
            use_alter=True,
        ),
    )

    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assistant_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        server_default=text("'running'"),
    )
    stop_reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        server_default=text("''"),
    )
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
    last_tool: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    workspace_fingerprint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("repository_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    session = relationship("AgentSession")
    project = relationship("Project")
    snapshot = relationship("RepositorySnapshot")
