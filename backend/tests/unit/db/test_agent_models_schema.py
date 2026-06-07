from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import get_args, get_origin, get_type_hints
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy import inspect
from sqlalchemy.orm import Mapped

from app.db.base import Base
from app.db.models import (
    AgentArtifact,
    AgentMessage,
    AgentRun,
    AgentRunEvent,
    AgentSession,
    RepositorySnapshot,
)

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


def test_repo_agent_tables_are_registered() -> None:
    expected_tables = {
        "agent_sessions",
        "agent_messages",
        "agent_runs",
        "agent_run_events",
        "agent_artifacts",
        "repository_snapshots",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_agent_sessions_schema_includes_required_columns(db_session) -> None:
    columns = _get_table_columns(db_session, "agent_sessions")

    assert columns["project_id"]["type"] == "BIGINT"
    assert columns["created_by"]["type"] == "BIGINT"
    assert columns["title"]["type"] == "VARCHAR(200)"
    assert columns["title"]["nullable"] == "False"
    assert columns["branch"]["type"] == "VARCHAR(255)"
    assert columns["branch"]["nullable"] == "False"
    assert columns["provider"]["type"] == "VARCHAR(64)"
    assert columns["model"]["type"] == "VARCHAR(128)"
    assert columns["last_workspace_fingerprint"]["type"] == "VARCHAR(128)"
    assert columns["last_runtime_identity_hash"]["type"] == "VARCHAR(128)"
    assert columns["status"]["nullable"] == "False"
    assert columns["memory_state"]["type"] == "JSON"
    assert columns["memory_state"]["default"] == "'{}'::json"
    assert columns["settings"]["type"] == "JSON"
    assert columns["settings"]["default"] == "'{}'::json"
    assert columns["last_message_at"]["type"] == "TIMESTAMP"


def test_repo_agent_orm_column_contracts_are_strict() -> None:
    assert str(AgentSession.__table__.c.title.type) == "VARCHAR(200)"
    assert AgentSession.__table__.c.title.nullable is False
    assert AgentSession.__table__.c.branch.nullable is False
    assert str(AgentSession.__table__.c.provider.type) == "VARCHAR(64)"
    assert str(AgentSession.__table__.c.model.type) == "VARCHAR(128)"
    assert str(AgentSession.__table__.c.last_workspace_fingerprint.type) == "VARCHAR(128)"
    assert str(AgentSession.__table__.c.last_runtime_identity_hash.type) == "VARCHAR(128)"

    assert str(AgentRun.__table__.c.status.server_default.arg) == "'running'"
    assert str(RepositorySnapshot.__table__.c.recent_commits_summary.server_default.arg) == "'[]'::json"
    assert str(AgentMessage.__table__.c.metadata.type) == "JSON"
    assert str(RepositorySnapshot.__table__.c.metadata.type) == "JSON"

    repository_snapshot_hints = get_type_hints(RepositorySnapshot, include_extras=True)
    recent_commits_type = repository_snapshot_hints["recent_commits_summary"]

    assert get_origin(recent_commits_type) is Mapped
    assert get_args(recent_commits_type) == (list[str],)


def test_repo_agent_orm_consistency_constraints_are_declared() -> None:
    session_constraints = {constraint.name for constraint in AgentSession.__table__.constraints}
    run_constraints = {constraint.name for constraint in AgentRun.__table__.constraints}
    message_constraints = {constraint.name for constraint in AgentMessage.__table__.constraints}
    event_constraints = {constraint.name for constraint in AgentRunEvent.__table__.constraints}
    artifact_constraints = {constraint.name for constraint in AgentArtifact.__table__.constraints}

    assert "uq_agent_sessions_id_project_id" in session_constraints
    assert "uq_agent_runs_id_session_id" in run_constraints
    assert "uq_agent_messages_id_session_id" in message_constraints

    assert "fk_agent_runs_session_project" in run_constraints
    assert "fk_agent_runs_user_message_session" in run_constraints
    assert "fk_agent_runs_assistant_message_session" in run_constraints
    assert "fk_agent_messages_run_session" in message_constraints
    assert "fk_agent_run_events_run_session" in event_constraints
    assert "fk_agent_artifacts_run_session" in artifact_constraints


def test_repo_agent_indexes_are_declared() -> None:
    session_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in AgentSession.__table__.indexes
    }
    message_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in AgentMessage.__table__.indexes
    }
    run_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in AgentRun.__table__.indexes
    }
    event_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in AgentRunEvent.__table__.indexes
    }
    snapshot_indexes = {
        (index.name, tuple(column.name for column in index.columns), index.unique)
        for index in RepositorySnapshot.__table__.indexes
    }

    assert ("ix_agent_sessions_project_updated", ("project_id", "updated_at"), False) in session_indexes
    assert ("ix_agent_sessions_project_branch", ("project_id", "branch"), False) in session_indexes
    assert (
        "ix_agent_messages_session_sequence",
        ("session_id", "sequence"),
        True,
    ) in message_indexes
    assert ("ix_agent_runs_session_created", ("session_id", "created_at"), False) in run_indexes
    assert (
        "ix_agent_run_events_run_sequence",
        ("run_id", "sequence"),
        False,
    ) in event_indexes
    assert (
        "ix_repository_snapshots_project_branch_head",
        ("project_id", "branch", "head_sha"),
        False,
    ) in snapshot_indexes
    assert (
        "ix_repository_snapshots_workspace_fingerprint",
        ("workspace_fingerprint",),
        False,
    ) in snapshot_indexes


def test_repo_agent_alembic_migration_builds_expected_tables_indexes_and_defaults() -> None:
    db_name = f"repo_agent_schema_{uuid4().hex[:8]}"

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

        with psycopg.connect(f"postgresql://postgres:postgres@localhost:5432/{db_name}") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename IN (
                        'agent_sessions',
                        'agent_messages',
                        'agent_runs',
                        'agent_run_events',
                        'agent_artifacts',
                        'repository_snapshots'
                      )
                    ORDER BY tablename
                    """
                )
                table_names = {row[0] for row in cur.fetchall()}

                cur.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename IN ('agent_sessions', 'agent_messages', 'agent_runs', 'agent_run_events', 'repository_snapshots')
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
                        'agent_sessions',
                        'agent_messages',
                        'agent_runs',
                        'agent_run_events',
                        'agent_artifacts',
                        'repository_snapshots'
                      )
                      AND column_name IN (
                        'status',
                        'memory_state',
                        'settings',
                        'tool_steps',
                        'attempts',
                        'prompt_metadata',
                        'completion_metadata',
                        'report_payload',
                        'payload',
                        'content_format',
                        'metadata',
                        'file_tree_summary',
                        'project_docs_summary',
                        'recent_commits_summary'
                      )
                    """
                )
                defaults = {
                    (table_name, column_name): column_default
                    for table_name, column_name, column_default in cur.fetchall()
                }

                cur.execute(
                    """
                    SELECT conname, contype, conrelid::regclass::text
                    FROM pg_constraint
                    WHERE connamespace = 'public'::regnamespace
                      AND conname IN (
                        'uq_agent_sessions_id_project_id',
                        'uq_agent_runs_id_session_id',
                        'uq_agent_messages_id_session_id',
                        'fk_agent_runs_session_project',
                        'fk_agent_messages_run_session',
                        'fk_agent_run_events_run_session',
                        'fk_agent_artifacts_run_session',
                        'fk_agent_runs_user_message_session',
                        'fk_agent_runs_assistant_message_session'
                      )
                    ORDER BY conname
                    """
                )
                constraints = {
                    constraint_name: {
                        "type": constraint_type,
                        "table": table_name,
                    }
                    for constraint_name, constraint_type, table_name in cur.fetchall()
                }

                cur.execute(
                    """
                    SELECT table_name, column_name, is_nullable, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND (
                        (table_name = 'agent_sessions' AND column_name IN (
                          'title',
                          'branch',
                          'provider',
                          'model',
                          'last_workspace_fingerprint',
                          'last_runtime_identity_hash'
                        ))
                        OR (table_name = 'repository_snapshots' AND column_name = 'recent_commits_summary')
                      )
                    ORDER BY table_name, column_name
                    """
                )
                column_contracts = {
                    (table_name, column_name): {
                        "nullable": is_nullable,
                        "data_type": data_type,
                        "max_length": character_maximum_length,
                    }
                    for table_name, column_name, is_nullable, data_type, character_maximum_length in cur.fetchall()
                }

        assert table_names == {
            "agent_artifacts",
            "agent_messages",
            "agent_run_events",
            "agent_runs",
            "agent_sessions",
            "repository_snapshots",
        }

        assert "(project_id, updated_at)" in index_definitions["ix_agent_sessions_project_updated"]
        assert "(project_id, branch)" in index_definitions["ix_agent_sessions_project_branch"]
        assert "CREATE UNIQUE INDEX" in index_definitions["ix_agent_messages_session_sequence"]
        assert "(session_id, sequence)" in index_definitions["ix_agent_messages_session_sequence"]
        assert "(session_id, created_at)" in index_definitions["ix_agent_runs_session_created"]
        assert "(run_id, sequence)" in index_definitions["ix_agent_run_events_run_sequence"]
        assert "(project_id, branch, head_sha)" in index_definitions[
            "ix_repository_snapshots_project_branch_head"
        ]
        assert "(workspace_fingerprint)" in index_definitions[
            "ix_repository_snapshots_workspace_fingerprint"
        ]

        assert constraints["uq_agent_sessions_id_project_id"] == {
            "type": "u",
            "table": "agent_sessions",
        }
        assert constraints["uq_agent_runs_id_session_id"] == {
            "type": "u",
            "table": "agent_runs",
        }
        assert constraints["uq_agent_messages_id_session_id"] == {
            "type": "u",
            "table": "agent_messages",
        }
        assert constraints["fk_agent_runs_session_project"] == {
            "type": "f",
            "table": "agent_runs",
        }
        assert constraints["fk_agent_messages_run_session"] == {
            "type": "f",
            "table": "agent_messages",
        }
        assert constraints["fk_agent_run_events_run_session"] == {
            "type": "f",
            "table": "agent_run_events",
        }
        assert constraints["fk_agent_artifacts_run_session"] == {
            "type": "f",
            "table": "agent_artifacts",
        }
        assert constraints["fk_agent_runs_user_message_session"] == {
            "type": "f",
            "table": "agent_runs",
        }
        assert constraints["fk_agent_runs_assistant_message_session"] == {
            "type": "f",
            "table": "agent_runs",
        }

        assert column_contracts[("agent_sessions", "title")] == {
            "nullable": "NO",
            "data_type": "character varying",
            "max_length": 200,
        }
        assert column_contracts[("agent_sessions", "branch")] == {
            "nullable": "NO",
            "data_type": "character varying",
            "max_length": 255,
        }
        assert column_contracts[("agent_sessions", "provider")] == {
            "nullable": "YES",
            "data_type": "character varying",
            "max_length": 64,
        }
        assert column_contracts[("agent_sessions", "model")] == {
            "nullable": "YES",
            "data_type": "character varying",
            "max_length": 128,
        }
        assert column_contracts[("agent_sessions", "last_workspace_fingerprint")] == {
            "nullable": "YES",
            "data_type": "character varying",
            "max_length": 128,
        }
        assert column_contracts[("agent_sessions", "last_runtime_identity_hash")] == {
            "nullable": "YES",
            "data_type": "character varying",
            "max_length": 128,
        }
        assert column_contracts[("repository_snapshots", "recent_commits_summary")] == {
            "nullable": "NO",
            "data_type": "json",
            "max_length": None,
        }

        assert defaults[("agent_sessions", "status")] == "'active'::character varying"
        assert defaults[("agent_sessions", "memory_state")] == "'{}'::json"
        assert defaults[("agent_sessions", "settings")] == "'{}'::json"
        assert defaults[("agent_messages", "content_format")] == "'markdown'::character varying"
        assert defaults[("agent_messages", "metadata")] == "'{}'::json"
        assert defaults[("agent_runs", "status")] == "'running'::character varying"
        assert defaults[("agent_runs", "tool_steps")] == "0"
        assert defaults[("agent_runs", "attempts")] == "0"
        assert defaults[("agent_runs", "prompt_metadata")] == "'{}'::json"
        assert defaults[("agent_runs", "completion_metadata")] == "'{}'::json"
        assert defaults[("agent_runs", "report_payload")] == "'{}'::json"
        assert defaults[("agent_run_events", "payload")] == "'{}'::json"
        assert defaults[("agent_artifacts", "metadata")] == "'{}'::json"
        assert defaults[("repository_snapshots", "metadata")] == "'{}'::json"
        assert defaults[("repository_snapshots", "file_tree_summary")] == "'{}'::json"
        assert defaults[("repository_snapshots", "project_docs_summary")] == "'{}'::json"
        assert defaults[("repository_snapshots", "recent_commits_summary")] == "'[]'::json"

        subprocess.run(
            ["alembic", "downgrade", "0003_webhook_review_execution"],
            cwd=BACKEND_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        with psycopg.connect(f"postgresql://postgres:postgres@localhost:5432/{db_name}") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename IN (
                        'agent_sessions',
                        'agent_messages',
                        'agent_runs',
                        'agent_run_events',
                        'agent_artifacts',
                        'repository_snapshots'
                      )
                    """
                )
                downgraded_tables = {row[0] for row in cur.fetchall()}

        assert downgraded_tables == set()
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
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
