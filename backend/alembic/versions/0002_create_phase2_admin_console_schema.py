"""create phase2 admin console schema

Revision ID: 0002_phase2_admin_console_schema
Revises: 0001_create_auth_rbac_schema
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_phase2_admin_console_schema"
down_revision = "0001_create_auth_rbac_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("file_extensions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("review_prompt_template", sa.Text(), nullable=True),
        sa.Column("prompt_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
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
    )
    op.create_index(
        "ix_project_templates_code",
        "project_templates",
        ["code"],
        unique=True,
    )

    op.create_table(
        "llm_models",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_key_masked", sa.String(length=255), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("prompt_template", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ux_llm_models_single_default",
        "llm_models",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "notification_bots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("bot_type", sa.String(length=50), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=True),
        sa.Column("secret_masked", sa.String(length=255), nullable=True),
        sa.Column("mention_strategy", sa.String(length=50), nullable=True),
        sa.Column("template_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
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
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("platform_type", sa.String(length=50), nullable=False),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("review_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("template_id", sa.BigInteger(), nullable=True),
        sa.Column("default_model_id", sa.BigInteger(), nullable=True),
        sa.Column("default_bot_id", sa.BigInteger(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["default_bot_id"], ["notification_bots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["default_model_id"], ["llm_models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["project_templates.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_projects_key", "projects", ["key"], unique=True)

    op.create_table(
        "review_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("project_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("template_id_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("template_name_snapshot", sa.String(length=100), nullable=True),
        sa.Column("review_prompt_snapshot", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("source_branch", sa.String(length=255), nullable=True),
        sa.Column("target_branch", sa.String(length=255), nullable=True),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("commit_messages", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("review_result", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("url_slug", sa.String(length=255), nullable=True),
        sa.Column("last_commit_id", sa.String(length=255), nullable=True),
        sa.Column("additions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("agent_trace", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("webhook_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("extra_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
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
    )
    op.create_index(
        "ix_review_records_project_event_created_at",
        "review_records",
        ["project_id", "event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_review_records_external_event_id",
        "review_records",
        ["external_event_id"],
        unique=False,
    )

    op.create_table(
        "review_commits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("review_record_id", sa.BigInteger(), nullable=False),
        sa.Column("commit_id", sa.String(length=255), nullable=False),
        sa.Column("short_commit_id", sa.String(length=64), nullable=True),
        sa.Column("author", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["review_record_id"],
            ["review_records.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_review_commits_review_record_id",
        "review_commits",
        ["review_record_id"],
        unique=False,
    )
    op.create_index(
        "ux_review_commits_record_sequence",
        "review_commits",
        ["review_record_id", "sequence"],
        unique=True,
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("member_name", sa.String(length=100), nullable=False),
        sa.Column("member_email", sa.String(length=255), nullable=True),
        sa.Column("role_name", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_project_members_project_id",
        "project_members",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ux_project_members_project_user",
        "project_members",
        ["project_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("username_snapshot", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=True),
        sa.Column("resource_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("request_path", sa.String(length=255), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ux_project_members_project_user", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")
    op.drop_index("ux_review_commits_record_sequence", table_name="review_commits")
    op.drop_index("ix_review_commits_review_record_id", table_name="review_commits")
    op.drop_table("review_commits")
    op.drop_index(
        "ix_review_records_external_event_id",
        table_name="review_records",
    )
    op.drop_index(
        "ix_review_records_project_event_created_at",
        table_name="review_records",
    )
    op.drop_table("review_records")
    op.drop_index("ix_projects_key", table_name="projects")
    op.drop_table("projects")
    op.drop_table("notification_bots")
    op.drop_index("ux_llm_models_single_default", table_name="llm_models")
    op.drop_table("llm_models")
    op.drop_index("ix_project_templates_code", table_name="project_templates")
    op.drop_table("project_templates")
