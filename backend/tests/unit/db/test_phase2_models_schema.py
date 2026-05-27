from sqlalchemy import inspect


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
