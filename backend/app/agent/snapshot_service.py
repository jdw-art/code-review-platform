from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from urllib.error import HTTPError

from app.agent.repository_provider import RepositoryContentDecodeError
from app.agent.workspace import (
    FileTreeSummary,
    NumberedFileSummary,
    WorkspaceSnapshot,
    normalize_workspace_project_id,
)
from app.db.models import Project

DOC_NAMES = ("README.md", "AGENTS.md", "pyproject.toml", "package.json")


class SnapshotService:
    def __init__(
        self,
        *,
        provider,
        doc_names: Sequence[str] = DOC_NAMES,
        doc_line_limit: int = 60,
        commit_limit: int = 5,
    ) -> None:
        self.provider = provider
        self.doc_names = tuple(doc_names)
        self.doc_line_limit = doc_line_limit
        self.commit_limit = commit_limit

    def build(
        self,
        *,
        branch: str,
        project: Project | None = None,
        project_id: int | str | None = None,
        platform_type: str | None = None,
        default_branch: str | None = None,
    ) -> WorkspaceSnapshot:
        resolved_project_id, resolved_platform_type, resolved_default_branch = self._resolve_project_fields(
            project=project,
            project_id=project_id,
            platform_type=platform_type,
            default_branch=default_branch,
        )
        head_sha = self.provider.resolve_branch_head(branch=branch)
        file_tree_summary = self.provider.list_tree(branch=branch, path=".", ref=head_sha)
        project_docs_summary: dict[str, object] = {}
        for doc_name in self.doc_names:
            try:
                project_docs_summary[doc_name] = self.provider.read_file(
                    branch=branch,
                    path=doc_name,
                    start=1,
                    end=self.doc_line_limit,
                    ref=head_sha,
                )
            except HTTPError as exc:
                if exc.code != 404:
                    raise
            except (KeyError, FileNotFoundError, RepositoryContentDecodeError):
                continue
        recent_commits_summary = self.provider.get_recent_commits(
            branch=branch,
            limit=self.commit_limit,
            ref=head_sha,
        )
        snapshot_digest = self._build_snapshot_digest(
            branch=branch,
            head_sha=head_sha,
            file_tree_summary=file_tree_summary,
            project_docs_summary=project_docs_summary,
            recent_commits_summary=recent_commits_summary,
        )
        return WorkspaceSnapshot(
            project_id=resolved_project_id,
            platform_type=resolved_platform_type,
            branch=branch,
            head_sha=head_sha,
            default_branch=resolved_default_branch,
            snapshot_digest=snapshot_digest,
            project_docs_summary=project_docs_summary,
            recent_commits_summary=recent_commits_summary,
            file_tree_summary=file_tree_summary,
        )

    @staticmethod
    def _resolve_project_fields(
        *,
        project: Project | None,
        project_id: int | str | None,
        platform_type: str | None,
        default_branch: str | None,
    ) -> tuple[str, str, str]:
        resolved_project_id = project.id if project is not None else project_id
        resolved_platform_type = project.platform_type if project is not None else platform_type
        resolved_default_branch = project.default_branch if project is not None else default_branch
        if resolved_project_id is None:
            raise ValueError("Missing project id for workspace snapshot")
        if not resolved_platform_type:
            raise ValueError("Missing platform type for workspace snapshot")
        if not resolved_default_branch:
            raise ValueError("Missing default branch for workspace snapshot")
        return (
            normalize_workspace_project_id(resolved_project_id),
            str(resolved_platform_type),
            str(resolved_default_branch),
        )

    @staticmethod
    def _build_snapshot_digest(
        *,
        branch: str,
        head_sha: str,
        file_tree_summary: FileTreeSummary,
        project_docs_summary: dict[str, NumberedFileSummary],
        recent_commits_summary: list[str],
    ) -> str:
        payload = {
            "branch": branch,
            "head_sha": head_sha,
            "file_tree_summary": file_tree_summary,
            "project_docs_summary": project_docs_summary,
            "recent_commits_summary": recent_commits_summary,
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
