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
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin


class AgentMessage(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        UniqueConstraint("id", "session_id", name="uq_agent_messages_id_session_id"),
        ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_messages_run_session",
        ),
        Index("ix_agent_messages_session_sequence", "session_id", "sequence", unique=True),
    )

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="markdown",
        server_default=text("'markdown'"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="completed",
        server_default=text("'completed'"),
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session = relationship("AgentSession", back_populates="messages")
    run = relationship("AgentRun", back_populates="messages", foreign_keys=[run_id])
