from __future__ import annotations

import anyio
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.db.models import Menu, Permission, Project, ProjectTemplate, User
from app.schemas.common import DomainConflictError
from app.schemas.pagination import PageQuery
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
)
from app.schemas.project_template import ProjectTemplateCreateRequest
from app.services.admin_console_bootstrap import (
    ADMIN_CONSOLE_PERMISSION_SEEDS,
    SYSTEM_PROJECT_TEMPLATE_SEEDS,
    bootstrap_admin_console_resources,
)
from app.services.project_service import ProjectService
from app.services.project_template_service import ProjectTemplateService


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


def test_create_project_rejects_duplicate_key(
    db_session,
    admin_user,
) -> None:
    existing_project = Project(
        name="Existing Project",
        key="demo-project",
        platform_type="gitlab",
        default_branch="main",
        review_enabled=True,
        settings={},
        created_by=admin_user.id,
    )
    db_session.add(existing_project)
    db_session.commit()

    service = ProjectService(session=db_session)
    payload = ProjectCreateRequest(
        name="Duplicate Project",
        key="demo-project",
        platform_type="github",
        default_branch="main",
    )

    with pytest.raises(DomainConflictError) as exc_info:
        anyio.run(service.create_project, admin_user, payload)

    assert exc_info.value.code == "PROJECT_KEY_ALREADY_EXISTS"


def test_create_project_translates_integrity_error_to_domain_conflict(
    db_session,
    admin_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ProjectService(session=db_session)
    payload = ProjectCreateRequest(
        name="Race Project",
        key="race-project",
        platform_type="gitlab",
        default_branch="main",
    )

    def raise_integrity_error() -> None:
        raise IntegrityError("insert into projects", {}, Exception("duplicate key"))

    monkeypatch.setattr(db_session, "commit", raise_integrity_error)

    with pytest.raises(DomainConflictError) as exc_info:
        anyio.run(service.create_project, admin_user, payload)

    assert exc_info.value.code == "PROJECT_KEY_ALREADY_EXISTS"


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


def test_create_template_translates_integrity_error_to_domain_conflict(
    db_session,
    admin_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ProjectTemplateService(session=db_session)
    payload = ProjectTemplateCreateRequest(
        name="Race Template",
        code="race-template",
        file_extensions=[".py"],
        prompt_metadata={},
    )

    def raise_integrity_error() -> None:
        raise IntegrityError(
            "insert into project_templates",
            {},
            Exception("duplicate key"),
        )

    monkeypatch.setattr(db_session, "commit", raise_integrity_error)

    with pytest.raises(DomainConflictError) as exc_info:
        anyio.run(service.create_template, admin_user, payload)

    assert exc_info.value.code == "PROJECT_TEMPLATE_CODE_ALREADY_EXISTS"


def test_bootstrap_admin_console_resources_is_idempotent_and_repairs_menu_hierarchy(
    db_session,
) -> None:
    wrong_parent = Menu(
        name="Wrong Parent",
        path="/wrong-parent",
        sort=5,
        visible=True,
    )
    projects_menu = Menu(
        name="旧项目管理",
        path="/projects",
        parent=wrong_parent,
        sort=1,
        visible=False,
    )
    template_menu = Menu(
        name="旧项目模板管理",
        path="/project-templates",
        sort=2,
        visible=True,
    )
    db_session.add_all([wrong_parent, projects_menu, template_menu])
    db_session.commit()

    bootstrap_admin_console_resources(db_session)
    db_session.commit()
    bootstrap_admin_console_resources(db_session)
    db_session.commit()

    db_session.refresh(projects_menu)
    db_session.refresh(template_menu)

    permission_count = len(
        db_session.scalars(
            select(Permission.code).where(
                Permission.code.in_([seed["code"] for seed in ADMIN_CONSOLE_PERMISSION_SEEDS])
            )
        ).all()
    )
    permission_codes = set(
        db_session.scalars(
            select(Permission.code).where(
                Permission.code.in_([seed["code"] for seed in ADMIN_CONSOLE_PERMISSION_SEEDS])
            )
        ).all()
    )
    template_count = len(
        db_session.scalars(
            select(ProjectTemplate.code).where(
                ProjectTemplate.code.in_(
                    [seed["code"] for seed in SYSTEM_PROJECT_TEMPLATE_SEEDS]
                )
            )
        ).all()
    )

    assert projects_menu.parent_id is None
    assert projects_menu.name == "项目管理"
    assert projects_menu.is_system is True
    assert template_menu.parent_id == projects_menu.id
    assert template_menu.is_system is True
    system_menu = db_session.scalar(select(Menu).where(Menu.path == "/system"))
    users_menu = db_session.scalar(select(Menu).where(Menu.path == "/system/users"))
    roles_menu = db_session.scalar(select(Menu).where(Menu.path == "/system/roles"))

    assert system_menu is not None
    assert system_menu.parent_id is None
    assert users_menu is not None
    assert users_menu.parent_id == system_menu.id
    assert roles_menu is not None
    assert roles_menu.parent_id == system_menu.id
    assert permission_count == len(ADMIN_CONSOLE_PERMISSION_SEEDS)
    assert template_count == len(SYSTEM_PROJECT_TEMPLATE_SEEDS)
    assert {
        "user:read",
        "user:create",
        "user:update",
        "user:delete",
        "user:status",
        "user:reset-password",
        "user:assign-role",
        "role:read",
        "role:create",
        "role:update",
        "role:delete",
        "role:assign",
        "menu:read",
        "menu:create",
        "menu:update",
        "menu:delete",
    }.issubset(permission_codes)
