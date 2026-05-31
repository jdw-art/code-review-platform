from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ReviewRecord(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    """审查记录主表，统一承载 push 与合并请求事件。"""

    __tablename__ = "review_records"
    __table_args__ = (
        Index(
            "ix_review_records_project_event_created_at",
            "project_id",
            "event_type",
            "created_at",
        ),
        Index("ix_review_records_external_event_id", "external_event_id"),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_merge_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_pull_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_commit_sha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    template_id_snapshot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    template_name_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    commit_messages: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )
    delivery_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )
    review_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_commit_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    additions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    deletions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    agent_trace: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    webhook_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )

    project = relationship("Project", back_populates="review_records")
    commits = relationship(
        "ReviewCommit",
        back_populates="review_record",
        cascade="all, delete-orphan",
    )
