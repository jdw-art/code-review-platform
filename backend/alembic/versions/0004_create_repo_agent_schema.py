"""create repo agent schema

Revision ID: 0004_create_repo_agent_schema
Revises: 0004_pico_online_agent_schema
Create Date: 2026-06-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_create_repo_agent_schema"
down_revision = "0004_pico_online_agent_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("last_head_sha", sa.String(length=255), nullable=True),
        sa.Column("last_workspace_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("last_runtime_identity_hash", sa.String(length=128), nullable=True),
        sa.Column("memory_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "project_id", name="uq_agent_sessions_id_project_id"),
    )
    op.create_index(
        "ix_agent_sessions_project_updated",
        "agent_sessions",
        ["project_id", "updated_at"],
    )
    op.create_index(
        "ix_agent_sessions_project_branch",
        "agent_sessions",
        ["project_id", "branch"],
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_message_id", sa.BigInteger(), nullable=True),
        sa.Column("assistant_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("stop_reason", sa.String(length=100), nullable=True),
        sa.Column("tool_steps", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_tool", sa.String(length=100), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("head_sha", sa.String(length=255), nullable=True),
        sa.Column("workspace_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("runtime_identity_hash", sa.String(length=255), nullable=True),
        sa.Column("prompt_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "completion_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("report_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id", "project_id"],
            ["agent_sessions.id", "agent_sessions.project_id"],
            name="fk_agent_runs_session_project",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_agent_runs_id_session_id"),
    )
    op.create_index(
        "ix_agent_runs_session_created",
        "agent_runs",
        ["session_id", "created_at"],
    )

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "content_format",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'markdown'"),
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'completed'"),
        ),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_messages_run_session",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_agent_messages_id_session_id"),
    )
    op.create_index(
        "ix_agent_messages_session_sequence",
        "agent_messages",
        ["session_id", "sequence"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_agent_runs_user_message_id",
        "agent_runs",
        "agent_messages",
        ["user_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_agent_runs_assistant_message_id",
        "agent_runs",
        "agent_messages",
        ["assistant_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_agent_runs_user_message_session",
        "agent_runs",
        "agent_messages",
        ["user_message_id", "session_id"],
        ["id", "session_id"],
    )
    op.create_foreign_key(
        "fk_agent_runs_assistant_message_session",
        "agent_runs",
        "agent_messages",
        ["assistant_message_id", "session_id"],
        ["id", "session_id"],
    )

    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_run_events_run_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_run_events_run_sequence",
        "agent_run_events",
        ["run_id", "sequence"],
    )

    op.create_table(
        "agent_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["run_id", "session_id"],
            ["agent_runs.id", "agent_runs.session_id"],
            name="fk_agent_artifacts_run_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "repository_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("head_sha", sa.String(length=255), nullable=False),
        sa.Column("workspace_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("snapshot_digest", sa.String(length=255), nullable=False),
        sa.Column(
            "file_tree_summary",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "project_docs_summary",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "recent_commits_summary",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_snapshots_project_branch_head",
        "repository_snapshots",
        ["project_id", "branch", "head_sha"],
    )
    op.create_index(
        "ix_repository_snapshots_workspace_fingerprint",
        "repository_snapshots",
        ["workspace_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_repository_snapshots_workspace_fingerprint", table_name="repository_snapshots")
    op.drop_index("ix_repository_snapshots_project_branch_head", table_name="repository_snapshots")
    op.drop_table("repository_snapshots")
    op.drop_table("agent_artifacts")
    op.drop_index("ix_agent_run_events_run_sequence", table_name="agent_run_events")
    op.drop_table("agent_run_events")
    op.drop_constraint("fk_agent_runs_assistant_message_session", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_user_message_session", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_assistant_message_id", "agent_runs", type_="foreignkey")
    op.drop_constraint("fk_agent_runs_user_message_id", "agent_runs", type_="foreignkey")
    op.drop_index("ix_agent_messages_session_sequence", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_runs_session_created", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_agent_sessions_project_branch", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_project_updated", table_name="agent_sessions")
    op.drop_table("agent_sessions")
