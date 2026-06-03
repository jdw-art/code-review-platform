from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class RepositorySnapshot(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repository_snapshots"
    __table_args__ = (
        Index("ix_repository_snapshots_project_ref_head", "project_id", "ref", "head_sha"),
        Index("ix_repository_snapshots_fingerprint", "fingerprint", unique=True),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform_type: Mapped[str] = mapped_column(String(32), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    file_tree: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    overview: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    recent_commits: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    indexed_paths: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project")
