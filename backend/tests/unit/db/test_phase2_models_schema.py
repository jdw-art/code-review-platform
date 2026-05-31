from __future__ import annotations

import os
import subprocess
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy import inspect, select

from app.db.models import LlmModel, Project, ProjectMember, ReviewCommit, ReviewRecord

POSTGRES_ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _get_table_columns(db_session, table_name: str) -> dict[str, dict[str, str]]:
    inspector = inspect(db_session.bind)
    return {
        column["name"]: {
            "type": str(column["type"]),
            "nullable": str(column["nullable"]),
            "default": str(column["default"]),
        }
        for column in inspector.get_columns(table_name)
    }


def test_phase2_admin_console_tables_exist(db_session) -> None:
    inspector = inspect(db_session.bind)
    table_names = set(inspector.get_table_names())

    assert "projects" in table_names
    assert "project_templates" in table_names
    assert "llm_models" in table_names
    assert "notification_bots" in table_names
    assert "review_records" in table_names
    assert "review_commits" in table_names
    assert "project_members" in table_names
    assert "audit_logs" in table_names


def test_review_records_keep_template_snapshots(db_session) -> None:
    inspector = inspect(db_session.bind)
    columns = {column["name"] for column in inspector.get_columns("review_records")}

    assert "template_id_snapshot" in columns
    assert "template_name_snapshot" in columns
    assert "review_prompt_snapshot" in columns


def test_review_record_schema_includes_execution_columns(db_session) -> None:
    columns = _get_table_columns(db_session, "review_records")

    assert columns["platform_type"]["type"] == "VARCHAR(32)"
    assert columns["platform_type"]["nullable"] == "False"
    assert columns["delivery_status"]["type"] == "VARCHAR(32)"
    assert columns["delivery_status"]["nullable"] == "False"
    assert columns["delivery_status"]["default"] == "'pending'::character varying"
    assert columns["retry_count"]["type"] == "INTEGER"
    assert columns["retry_count"]["nullable"] == "False"
    assert columns["retry_count"]["default"] == "0"
    assert columns["error_message"]["type"] == "TEXT"
    assert columns["external_project_id"]["type"] == "VARCHAR(255)"


def test_phase2_operational_indexes_are_declared() -> None:
    review_record_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in ReviewRecord.__table__.indexes
    }
    llm_model_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in LlmModel.__table__.indexes
    }
    review_commit_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in ReviewCommit.__table__.indexes
    }
    project_member_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in ProjectMember.__table__.indexes
    }

    assert (
        "ix_review_records_external_event_id",
        ("external_event_id",),
        False,
    ) in review_record_indexes
    assert (
        "ux_llm_models_single_default",
        ("is_default",),
        True,
    ) in llm_model_indexes
    assert (
        "ix_review_commits_review_record_id",
        ("review_record_id",),
        False,
    ) in review_commit_indexes
    assert (
        "ux_review_commits_record_sequence",
        ("review_record_id", "sequence"),
        True,
    ) in review_commit_indexes
    assert (
        "ix_project_members_project_id",
        ("project_id",),
        False,
    ) in project_member_indexes
    assert (
        "ux_project_members_project_user",
        ("project_id", "user_id"),
        True,
    ) in project_member_indexes

    llm_model_default_index = next(
        index for index in LlmModel.__table__.indexes if index.name == "ux_llm_models_single_default"
    )
    project_member_user_index = next(
        index for index in ProjectMember.__table__.indexes if index.name == "ux_project_members_project_user"
    )

    assert str(llm_model_default_index.dialect_options["postgresql"]["where"]) == "is_default"
    assert (
        str(project_member_user_index.dialect_options["postgresql"]["where"])
        == "user_id IS NOT NULL"
    )


def test_phase2_alembic_migration_builds_expected_indexes_and_defaults() -> None:
    """验证 Alembic 真实落库后的索引与 JSON 默认值，防止 migration/ORM 漂移。"""

    db_name = f"phase2_schema_{uuid4().hex[:8]}"

    with psycopg.connect(POSTGRES_ADMIN_DSN, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    env = os.environ.copy()
    env.update(
        {
            "AI_CODE_REVIEWER_POSTGRES_HOST": "localhost",
            "AI_CODE_REVIEWER_POSTGRES_PORT": "5432",
            "AI_CODE_REVIEWER_POSTGRES_USER": "postgres",
            "AI_CODE_REVIEWER_POSTGRES_PASSWORD": "postgres",
            "AI_CODE_REVIEWER_POSTGRES_DB": db_name,
        }
    )

    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        with psycopg.connect(
            f"postgresql://postgres:postgres@localhost:5432/{db_name}"
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename IN ('llm_models', 'review_records', 'review_commits', 'project_members')
                    ORDER BY tablename, indexname
                    """
                )
                index_definitions = dict(cur.fetchall())

                cur.execute(
                    """
                    SELECT table_name, column_name, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name IN (
                        'project_templates',
                        'notification_bots',
                        'projects',
                        'review_records',
                        'review_commits',
                        'audit_logs'
                      )
                      AND column_name IN (
                        'delivery_status',
                        'file_extensions',
                        'prompt_metadata',
                        'template_config',
                        'settings',
                        'commit_messages',
                        'agent_trace',
                        'webhook_data',
                        'extra_data',
                        'payload',
                        'request_payload'
                      )
                    """
                )
                defaults = {
                    (table_name, column_name): column_default
                    for table_name, column_name, column_default in cur.fetchall()
                }

                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'review_records'
                      AND column_name IN (
                        'platform_type',
                        'delivery_status',
                        'external_project_id',
                        'external_merge_request_id',
                        'external_pull_request_id',
                        'external_commit_sha',
                        'reviewed_at',
                        'failed_at',
                        'error_message',
                        'retry_count'
                      )
                    ORDER BY column_name
                    """
                )
                execution_columns = {
                    column_name: {
                        "data_type": data_type,
                        "nullable": is_nullable,
                        "default": column_default,
                    }
                    for column_name, data_type, is_nullable, column_default in cur.fetchall()
                }

        assert "CREATE UNIQUE INDEX" in index_definitions["ux_llm_models_single_default"]
        assert "WHERE is_default" in index_definitions["ux_llm_models_single_default"]
        assert (
            "ix_review_records_external_event_id" in index_definitions
            and "UNIQUE" not in index_definitions["ix_review_records_external_event_id"]
        )
        assert "(project_id, event_type, created_at)" in index_definitions[
            "ix_review_records_project_event_created_at"
        ]
        assert "CREATE UNIQUE INDEX" in index_definitions["ux_review_commits_record_sequence"]
        assert "(review_record_id, sequence)" in index_definitions[
            "ux_review_commits_record_sequence"
        ]
        assert "CREATE UNIQUE INDEX" in index_definitions["ux_project_members_project_user"]
        assert "WHERE (user_id IS NOT NULL)" in index_definitions["ux_project_members_project_user"]

        assert defaults[("project_templates", "file_extensions")] == "'[]'::json"
        assert defaults[("project_templates", "prompt_metadata")] == "'{}'::json"
        assert defaults[("notification_bots", "template_config")] == "'{}'::json"
        assert defaults[("projects", "settings")] == "'{}'::json"
        assert defaults[("review_records", "delivery_status")] == "'pending'::character varying"
        assert defaults[("review_records", "commit_messages")] == "'[]'::json"
        assert defaults[("review_records", "agent_trace")] == "'{}'::json"
        assert defaults[("review_records", "webhook_data")] == "'{}'::json"
        assert defaults[("review_records", "extra_data")] == "'{}'::json"
        assert defaults[("review_commits", "payload")] == "'{}'::json"
        assert defaults[("audit_logs", "request_payload")] == "'{}'::json"
        assert execution_columns == {
            "delivery_status": {
                "data_type": "character varying",
                "nullable": "NO",
                "default": "'pending'::character varying",
            },
            "error_message": {
                "data_type": "text",
                "nullable": "YES",
                "default": None,
            },
            "external_commit_sha": {
                "data_type": "character varying",
                "nullable": "YES",
                "default": None,
            },
            "external_merge_request_id": {
                "data_type": "character varying",
                "nullable": "YES",
                "default": None,
            },
            "external_project_id": {
                "data_type": "character varying",
                "nullable": "YES",
                "default": None,
            },
            "external_pull_request_id": {
                "data_type": "character varying",
                "nullable": "YES",
                "default": None,
            },
            "failed_at": {
                "data_type": "timestamp with time zone",
                "nullable": "YES",
                "default": None,
            },
            "platform_type": {
                "data_type": "character varying",
                "nullable": "NO",
                "default": None,
            },
            "retry_count": {
                "data_type": "integer",
                "nullable": "NO",
                "default": "0",
            },
            "reviewed_at": {
                "data_type": "timestamp with time zone",
                "nullable": "YES",
                "default": None,
            },
        }

        subprocess.run(
            ["alembic", "downgrade", "0001_create_auth_rbac_schema"],
            cwd=BACKEND_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        with psycopg.connect(
            f"postgresql://postgres:postgres@localhost:5432/{db_name}"
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN (
                        'projects',
                        'project_templates',
                        'llm_models',
                        'notification_bots',
                        'review_records',
                        'review_commits',
                        'project_members',
                        'audit_logs'
                      )
                    ORDER BY table_name
                    """
                )
                phase2_tables = [row[0] for row in cur.fetchall()]

        assert phase2_tables == []
    finally:
        with psycopg.connect(POSTGRES_ADMIN_DSN, autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()"
                ),
                [db_name],
            )
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name))
            )


def test_deleting_project_relies_on_db_cascade_for_children(db_session) -> None:
    project = Project(
        name="Phase 2 Project",
        key="phase-2-project",
        platform_type="github",
        default_branch="main",
    )
    db_session.add(project)
    db_session.flush()

    review_record = ReviewRecord(
        project_id=project.id,
        event_type="push",
        platform_type=project.platform_type,
        project_name_snapshot=project.name,
        author="alice",
    )
    project_member = ProjectMember(
        project_id=project.id,
        member_name="alice",
    )
    db_session.add_all([review_record, project_member])
    db_session.commit()
    project_id = project.id
    review_record_id = review_record.id
    project_member_id = project_member.id

    db_session.delete(project)
    db_session.commit()

    assert db_session.scalar(select(Project).where(Project.id == project_id)) is None
    assert db_session.scalar(select(ReviewRecord).where(ReviewRecord.id == review_record_id)) is None
    assert (
        db_session.scalar(select(ProjectMember).where(ProjectMember.id == project_member_id))
        is None
    )
