"""add webhook review execution schema

Revision ID: 0003_webhook_review_execution
Revises: 0002_phase2_admin_console_schema
Create Date: 2026-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_webhook_review_execution"
down_revision = "0002_phase2_admin_console_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_records",
        sa.Column("platform_type", sa.String(length=32), nullable=True),
    )
    op.execute(
        """
        UPDATE review_records AS rr
        SET platform_type = p.platform_type
        FROM projects AS p
        WHERE rr.project_id = p.id
          AND rr.platform_type IS NULL
        """
    )
    op.alter_column("review_records", "platform_type", nullable=False)
    op.add_column(
        "review_records",
        sa.Column(
            "delivery_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.add_column(
        "review_records",
        sa.Column("external_project_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("external_merge_request_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("external_pull_request_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("external_commit_sha", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "review_records",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("review_records", "retry_count")
    op.drop_column("review_records", "error_message")
    op.drop_column("review_records", "failed_at")
    op.drop_column("review_records", "reviewed_at")
    op.drop_column("review_records", "external_commit_sha")
    op.drop_column("review_records", "external_pull_request_id")
    op.drop_column("review_records", "external_merge_request_id")
    op.drop_column("review_records", "external_project_id")
    op.drop_column("review_records", "delivery_status")
    op.drop_column("review_records", "platform_type")
