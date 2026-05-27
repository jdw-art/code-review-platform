from __future__ import annotations

import anyio
import pytest
from sqlalchemy import select

from app.db.models import Project, ProjectTemplate, User
from app.schemas.common import DomainConflictError
from app.schemas.pagination import PageQuery
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectService


@pytest.fixture
def admin_user(db_session) -> User:
    user = User(
        username="project-admin",
        password_hash="hashed-password",
        is_active=True,
        is_superuser=True,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_project_template(db_session) -> ProjectTemplate:
    template = ProjectTemplate(
        name="Java Default",
        code="java-default",
        description="Java backend template",
        file_extensions=[".java", ".xml"],
        review_prompt_template="review java changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=True,
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def inactive_project_template(db_session) -> ProjectTemplate:
    template = ProjectTemplate(
        name="Inactive Template",
        code="inactive-template",
        description="Disabled template",
        file_extensions=[".go"],
        review_prompt_template="review go changes",
        prompt_metadata={},
        is_system=False,
        is_active=False,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def test_create_project_rejects_inactive_template(
    db_session,
    admin_user,
    inactive_project_template,
) -> None:
    service = ProjectService(session=db_session)
    payload = ProjectCreateRequest(
        name="Demo Project",
        key="demo-project",
        platform_type="gitlab",
        default_branch="main",
        template_id=inactive_project_template.id,
    )

    with pytest.raises(DomainConflictError) as exc_info:
        anyio.run(service.create_project, admin_user, payload)

    assert exc_info.value.code == "PROJECT_TEMPLATE_INACTIVE"


def test_create_project_persists_creator_and_template_binding(
    db_session,
    admin_user,
    active_project_template,
) -> None:
    service = ProjectService(session=db_session)
    payload = ProjectCreateRequest(
        name="Demo Project",
        key="demo-project",
        platform_type="github",
        repo_url="https://example.com/demo.git",
        default_branch="main",
        description="Project for admin console tests",
        template_id=active_project_template.id,
        review_enabled=True,
        settings={"language": "java"},
    )

    result = anyio.run(service.create_project, admin_user, payload)

    assert isinstance(result.id, int)
    assert result.name == "Demo Project"
    assert result.template is not None
    assert result.template.id == active_project_template.id
    assert result.created_by == admin_user.id

    project = db_session.scalar(select(Project).where(Project.id == result.id))
    assert project is not None
    assert project.created_by == admin_user.id
    assert project.template_id == active_project_template.id


def test_update_project_rejects_switching_to_inactive_template(
    db_session,
    admin_user,
    active_project_template,
    inactive_project_template,
) -> None:
    project = Project(
        name="Demo Project",
        key="demo-project",
        platform_type="gitlab",
        default_branch="main",
        template_id=active_project_template.id,
        review_enabled=True,
        settings={},
        created_by=admin_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    service = ProjectService(session=db_session)
    payload = ProjectUpdateRequest(
        name="Demo Project",
        key="demo-project",
        platform_type="gitlab",
        repo_url=None,
        default_branch="develop",
        description="Updated",
        template_id=inactive_project_template.id,
        review_enabled=False,
        settings={"language": "go"},
    )

    with pytest.raises(DomainConflictError) as exc_info:
        anyio.run(service.update_project, admin_user, project.id, payload)

    assert exc_info.value.code == "PROJECT_TEMPLATE_INACTIVE"


def test_list_projects_returns_paginated_rows(
    db_session,
    admin_user,
    active_project_template,
) -> None:
    first = Project(
        name="Alpha",
        key="alpha",
        platform_type="gitlab",
        default_branch="main",
        template_id=active_project_template.id,
        review_enabled=True,
        settings={},
        created_by=admin_user.id,
    )
    second = Project(
        name="Beta",
        key="beta",
        platform_type="github",
        default_branch="main",
        template_id=None,
        review_enabled=False,
        settings={"language": "ts"},
        created_by=admin_user.id,
    )
    db_session.add_all([first, second])
    db_session.commit()

    service = ProjectService(session=db_session)

    result = anyio.run(service.list_projects, PageQuery(page=1, page_size=1))

    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 1
    assert len(result.items) == 1
    assert result.items[0].name == "Alpha"


def test_update_project_status_toggles_is_active(
    db_session,
    admin_user,
) -> None:
    project = Project(
        name="Toggle Project",
        key="toggle-project",
        platform_type="gitlab",
        default_branch="main",
        review_enabled=True,
        settings={},
        created_by=admin_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    service = ProjectService(session=db_session)

    result = anyio.run(
        service.update_status,
        admin_user,
        project.id,
        ProjectStatusUpdateRequest(is_active=False),
    )

    assert result.is_active is False
    db_session.refresh(project)
    assert project.is_active is False
