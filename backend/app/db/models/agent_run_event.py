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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin


class AgentRunEvent(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_run_events_run_session",
            ondelete="CASCADE",
        ),
        Index("ix_agent_run_events_run_sequence", "run_id", "sequence"),
    )

    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
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

    run = relationship("AgentRun", back_populates="events", foreign_keys=[run_id])
    session = relationship("AgentSession", back_populates="run_events")
