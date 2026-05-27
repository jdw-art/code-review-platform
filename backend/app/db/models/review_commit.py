from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin


class ReviewCommit(BigIntPrimaryKeyMixin, Base):
    """审查记录下的 commit 明细表。"""

    __tablename__ = "review_commits"
    __table_args__ = (
        Index("ix_review_commits_review_record_id", "review_record_id"),
        Index(
            "ux_review_commits_record_sequence",
            "review_record_id",
            "sequence",
            unique=True,
        ),
    )

    review_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("review_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    commit_id: Mapped[str] = mapped_column(String(255), nullable=False)
    short_commit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
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

    review_record = relationship("ReviewRecord", back_populates="commits")
