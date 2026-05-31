from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project
from app.schemas.common import DomainConflictError


class IntegrationProjectLocator:
    """Resolve an active internal project from external webhook repository identifiers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def locate(
        self,
        *,
        platform_type: str,
        repo_url: str | None,
        repo_full_name: str | None,
        external_project_id: str | None,
    ) -> Project | None:
        projects = self.session.scalars(
            select(Project).where(
                Project.platform_type == platform_type,
                Project.is_active.is_(True),
            )
        ).all()

        repo_url_match = self._match_by_repo_url(projects, repo_url)
        settings_name_match = self._match_by_settings_name(
            projects,
            platform_type=platform_type,
            repo_full_name=repo_full_name,
        )
        if repo_url_match is not None:
            return repo_url_match
        if settings_name_match is not None:
            return settings_name_match

        return self._match_by_external_project_id(
            projects,
            external_project_id,
        )

    def _match_by_repo_url(
        self,
        projects: list[Project],
        repo_url: str | None,
    ) -> Project | None:
        if not repo_url:
            return None

        matches = [project for project in projects if project.repo_url == repo_url]
        return self._resolve_unique_match(
            matches,
            conflict_code="PROJECT_WEBHOOK_AMBIGUOUS",
            message="Webhook repo URL matches multiple active projects.",
            details={"repo_url": repo_url},
        )

    def _match_by_settings_name(
        self,
        projects: list[Project],
        *,
        platform_type: str,
        repo_full_name: str | None,
    ) -> Project | None:
        if not repo_full_name:
            return None

        setting_key = (
            "gitlab_project_path" if platform_type == "gitlab" else "external_repo_full_name"
        )
        matches = [
            project
            for project in projects
            if str(project.settings.get(setting_key) or "") == repo_full_name
        ]
        return self._resolve_unique_match(
            matches,
            conflict_code="PROJECT_WEBHOOK_AMBIGUOUS",
            message="Webhook repository name matches multiple active projects.",
            details={
                "platform_type": platform_type,
                "repo_full_name": repo_full_name,
                "setting_key": setting_key,
            },
        )

    def _match_by_external_project_id(
        self,
        projects: list[Project],
        external_project_id: str | None,
    ) -> Project | None:
        if external_project_id is None:
            return None

        expected_id = str(external_project_id)
        matches = [
            project
            for project in projects
            if str(project.settings.get("external_project_id")) == expected_id
        ]
        return self._resolve_unique_match(
            matches,
            conflict_code="PROJECT_WEBHOOK_AMBIGUOUS",
            message="Webhook external project id matches multiple active projects.",
            details={"external_project_id": expected_id},
        )

    def _resolve_unique_match(
        self,
        matches: list[Project],
        *,
        conflict_code: str,
        message: str,
        details: dict[str, object],
    ) -> Project | None:
        if not matches:
            return None
        if len(matches) > 1:
            raise DomainConflictError(
                code=conflict_code,
                message=message,
                details={
                    **details,
                    "matched_project_ids": sorted(project.id for project in matches),
                },
            )
        return matches[0]
