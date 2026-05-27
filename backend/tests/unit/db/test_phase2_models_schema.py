from sqlalchemy import inspect, select

from app.db.models import Project, ProjectMember, ReviewRecord


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


def test_review_records_external_event_id_is_unique_in_schema() -> None:
    unique_constraint_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in ReviewRecord.__table__.constraints
        if getattr(constraint, "unique", False)
    }
    unique_index_columns = {
        tuple(column.name for column in index.columns)
        for index in ReviewRecord.__table__.indexes
        if index.unique
    }

    assert ("external_event_id",) in (unique_constraint_columns | unique_index_columns)


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
