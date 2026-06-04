from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class RepositorySnapshot(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repository_snapshots"
    __table_args__ = (
        Index(
            "ix_repository_snapshots_project_branch_head",
            "project_id",
            "branch",
            "head_sha",
        ),
        Index(
            "ix_repository_snapshots_workspace_fingerprint",
            "workspace_fingerprint",
        ),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_digest: Mapped[str] = mapped_column(String(255), nullable=False)
    file_tree_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    project_docs_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )
    recent_commits_summary: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )

    project = relationship("Project")
