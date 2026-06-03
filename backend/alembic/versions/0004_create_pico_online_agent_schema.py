"""create pico online agent schema

Revision ID: 0004_pico_online_agent_schema
Revises: 0003_webhook_review_execution
Create Date: 2026-06-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_pico_online_agent_schema"
down_revision = "0003_webhook_review_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_snapshots",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("platform_type", sa.String(length=32), nullable=False),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("ref", sa.String(length=255), nullable=False),
        sa.Column("head_sha", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("file_tree", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("overview", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("recent_commits", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("indexed_paths", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_snapshots_project_ref_head", "repository_snapshots", ["project_id", "ref", "head_sha"], unique=False)
    op.create_index("ix_repository_snapshots_fingerprint", "repository_snapshots", ["fingerprint"], unique=True)

    op.create_table(
        "agent_sessions",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("workspace_fingerprint", sa.String(length=128), nullable=False, server_default=sa.text("''")),
        sa.Column("snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("memory_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["repository_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "project_id", name="uq_agent_sessions_id_project"),
    )
    op.create_index("ix_agent_sessions_project_updated", "agent_sessions", ["project_id", "updated_at"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_message_id", sa.BigInteger(), nullable=True),
        sa.Column("assistant_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'running'")),
        sa.Column("stop_reason", sa.String(length=64), nullable=False, server_default=sa.text("''")),
        sa.Column("tool_steps", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_tool", sa.String(length=64), nullable=False, server_default=sa.text("''")),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("prompt_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("completion_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("workspace_fingerprint", sa.String(length=128), nullable=False, server_default=sa.text("''")),
        sa.Column("snapshot_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id", "project_id"],
            ["agent_sessions.id", "agent_sessions.project_id"],
            name="fk_agent_runs_session_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["snapshot_id"], ["repository_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_agent_runs_id_session"),
    )
    op.create_index("ix_agent_runs_session_created", "agent_runs", ["session_id", "created_at"], unique=False)
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"], unique=False)

    op.create_table(
        "agent_messages",
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(length=32), nullable=False, server_default=sa.text("'markdown'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'completed'")),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_messages_run_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_agent_messages_id_session"),
    )
    op.create_index("ix_agent_messages_session_sequence", "agent_messages", ["session_id", "sequence"], unique=True)
    op.create_index("ix_agent_messages_run_id", "agent_messages", ["run_id"], unique=False)
    op.create_foreign_key(
        "fk_agent_runs_user_message",
        "agent_runs",
        "agent_messages",
        ["user_message_id", "session_id"],
        ["id", "session_id"],
    )
    op.create_foreign_key(
        "fk_agent_runs_assistant_message",
        "agent_runs",
        "agent_messages",
        ["assistant_message_id", "session_id"],
        ["id", "session_id"],
    )

    op.create_table(
        "agent_run_events",
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_run_events_run_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_run_events_run_sequence", "agent_run_events", ["run_id", "sequence"], unique=True)
    op.create_index("ix_agent_run_events_session_id_id", "agent_run_events", ["session_id", "id"], unique=False)

    op.create_table(
        "agent_artifacts",
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_artifacts_run_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_artifacts_run_type", "agent_artifacts", ["run_id", "artifact_type"], unique=False)
    op.create_index("ix_agent_artifacts_session_id", "agent_artifacts", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_artifacts_session_id", table_name="agent_artifacts")
    op.drop_index("ix_agent_artifacts_run_type", table_name="agent_artifacts")
    op.drop_table("agent_artifacts")

    op.drop_index("ix_agent_run_events_session_id_id", table_name="agent_run_events")
    op.drop_index("ix_agent_run_events_run_sequence", table_name="agent_run_events")
    op.drop_table("agent_run_events")

    op.drop_constraint("fk_agent_runs_assistant_message", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_user_message", "agent_runs", type_="foreignkey")
    op.drop_index("ix_agent_messages_run_id", table_name="agent_messages")
    op.drop_index("ix_agent_messages_session_sequence", table_name="agent_messages")
    op.drop_table("agent_messages")

    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_session_created", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_agent_sessions_project_updated", table_name="agent_sessions")
    op.drop_table("agent_sessions")

    op.drop_index("ix_repository_snapshots_fingerprint", table_name="repository_snapshots")
    op.drop_index("ix_repository_snapshots_project_ref_head", table_name="repository_snapshots")
    op.drop_table("repository_snapshots")
