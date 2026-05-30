from __future__ import annotations

import pytest

from app.db.models import Project
from app.schemas.common import DomainConflictError
from app.services.integration_project_locator import IntegrationProjectLocator


def test_locator_matches_by_repo_url_first(db_session) -> None:
    project = Project(
        name="Repo URL Project",
        key="repo-url-project",
        platform_type="github",
        repo_url="https://github.com/acme/repo-url-project",
        default_branch="main",
        review_enabled=True,
        settings={"external_project_id": "999"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    locator = IntegrationProjectLocator(db_session)

    matched = locator.locate(
        platform_type="github",
        repo_url="https://github.com/acme/repo-url-project",
        repo_full_name="acme/ignored",
        external_project_id="123456",
    )

    assert matched is not None
    assert matched.id == project.id


def test_locator_falls_back_to_settings_full_name(db_session) -> None:
    project = Project(
        name="Full Name Project",
        key="full-name-project",
        platform_type="github",
        repo_url=None,
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/full-name-project"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    locator = IntegrationProjectLocator(db_session)

    matched = locator.locate(
        platform_type="github",
        repo_url=None,
        repo_full_name="acme/full-name-project",
        external_project_id=None,
    )

    assert matched is not None
    assert matched.id == project.id


def test_locator_raises_conflict_when_match_signals_point_to_different_projects(
    db_session,
) -> None:
    repo_url_project = Project(
        name="Repo URL Project",
        key="repo-url-project-conflict",
        platform_type="gitlab",
        repo_url="https://gitlab.com/acme/repo-url-project",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    full_name_project = Project(
        name="GitLab Path Project",
        key="gitlab-path-project",
        platform_type="gitlab",
        repo_url=None,
        default_branch="main",
        review_enabled=True,
        settings={"gitlab_project_path": "group/repo"},
    )
    external_id_project = Project(
        name="External Id Project",
        key="external-id-project",
        platform_type="gitlab",
        repo_url=None,
        default_branch="main",
        review_enabled=True,
        settings={"external_project_id": "42"},
    )
    db_session.add_all([repo_url_project, full_name_project, external_id_project])
    db_session.commit()
    db_session.refresh(repo_url_project)

    locator = IntegrationProjectLocator(db_session)

    matched = locator.locate(
        platform_type="gitlab",
        repo_url="https://gitlab.com/acme/repo-url-project",
        repo_full_name="group/repo",
        external_project_id="42",
    )

    assert matched is not None
    assert matched.id == repo_url_project.id


def test_locator_raises_conflict_when_repo_url_matches_multiple_projects(
    db_session,
) -> None:
    first_project = Project(
        name="First Repo URL Project",
        key="first-repo-url-project",
        platform_type="github",
        repo_url="https://github.com/acme/shared-repo",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    second_project = Project(
        name="Second Repo URL Project",
        key="second-repo-url-project",
        platform_type="github",
        repo_url="https://github.com/acme/shared-repo",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    db_session.add_all([first_project, second_project])
    db_session.commit()

    locator = IntegrationProjectLocator(db_session)

    with pytest.raises(DomainConflictError) as exc_info:
        locator.locate(
            platform_type="github",
            repo_url="https://github.com/acme/shared-repo",
            repo_full_name=None,
            external_project_id=None,
        )

    assert exc_info.value.code == "PROJECT_WEBHOOK_AMBIGUOUS"
