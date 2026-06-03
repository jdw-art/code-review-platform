from __future__ import annotations

from sqlalchemy import inspect

from app.db.base import Base


def test_agent_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert {
        "agent_sessions",
        "agent_messages",
        "agent_runs",
        "agent_run_events",
        "agent_artifacts",
        "repository_snapshots",
    } <= table_names


def test_agent_sessions_columns_exist(db_session) -> None:
    inspector = inspect(db_session.bind)
    columns = {column["name"] for column in inspector.get_columns("agent_sessions")}

    assert {
        "id",
        "project_id",
        "created_by",
        "title",
        "status",
        "provider",
        "model",
        "workspace_fingerprint",
        "snapshot_id",
        "memory_state",
        "settings",
        "last_message_at",
        "created_at",
        "updated_at",
    } <= columns


def test_agent_foreign_keys_and_defaults_exist(db_session) -> None:
    inspector = inspect(db_session.bind)

    run_event_columns = {
        column["name"]: column
        for column in inspector.get_columns("agent_run_events")
    }
    assert run_event_columns["payload"]["default"] == "'{}'::json"

    run_foreign_keys = inspector.get_foreign_keys("agent_runs")
    run_fk_names = {item["name"] for item in run_foreign_keys}
    assert {
        "fk_agent_runs_session_project",
        "fk_agent_runs_user_message",
        "fk_agent_runs_assistant_message",
    } <= run_fk_names

    message_foreign_keys = inspector.get_foreign_keys("agent_messages")
    assert "fk_agent_messages_run_session" in {item["name"] for item in message_foreign_keys}

    event_foreign_keys = inspector.get_foreign_keys("agent_run_events")
    assert "fk_agent_run_events_run_session" in {item["name"] for item in event_foreign_keys}

    artifact_foreign_keys = inspector.get_foreign_keys("agent_artifacts")
    assert "fk_agent_artifacts_run_session" in {item["name"] for item in artifact_foreign_keys}
