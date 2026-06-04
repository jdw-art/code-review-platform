from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin


class AgentArtifact(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "agent_artifacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_artifacts_run_session",
            ondelete="CASCADE",
        ),
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
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
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

    run = relationship("AgentRun", back_populates="artifacts", foreign_keys=[run_id])
    session = relationship("AgentSession", back_populates="artifacts")
