from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.repository_provider import RepositoryContentProvider
from app.agent.tools import READ_ONLY_TOOL_SPECS
from app.db.models import Project, RepositorySnapshot


class RepositorySnapshotService:
    def __init__(self, session: Session, *, commit_limit: int = 10) -> None:
        self.session = session
        self.commit_limit = int(commit_limit)

    def ensure_ready_snapshot(
        self,
        *,
        project: Project,
        provider: RepositoryContentProvider,
    ) -> RepositorySnapshot:
        ref = project.default_branch
        head_sha = provider.get_head_sha(ref=ref)
        self.mark_stale_snapshots(project_id=project.id, ref=ref, new_head_sha=head_sha)

        fingerprint = self.build_fingerprint(
            project_id=project.id,
            platform_type=project.platform_type,
            repo_url=project.repo_url,
            ref=ref,
            head_sha=head_sha,
            tool_signature=self._tool_signature(),
            settings_hash=self._settings_hash(project.settings),
        )
        existing = self.session.scalar(
            select(RepositorySnapshot)
            .where(
                RepositorySnapshot.project_id == project.id,
                RepositorySnapshot.ref == ref,
                RepositorySnapshot.head_sha == head_sha,
                RepositorySnapshot.fingerprint == fingerprint,
                RepositorySnapshot.status == "ready",
            )
            .order_by(RepositorySnapshot.id.desc())
        )
        if existing is not None:
            return existing

        file_tree = list(provider.get_file_tree(ref=ref))
        overview = dict(provider.get_snapshot_overview(ref=ref))
        recent_commits = list(provider.get_recent_commit_records(limit=self.commit_limit))
        snapshot = RepositorySnapshot(
            project_id=project.id,
            platform_type=project.platform_type,
            repo_url=project.repo_url,
            ref=ref,
            head_sha=head_sha,
            fingerprint=fingerprint,
            status="ready",
            file_tree=file_tree,
            overview=overview,
            recent_commits=recent_commits,
            indexed_paths=self._build_indexed_paths(file_tree),
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def mark_stale_snapshots(self, *, project_id: int, ref: str, new_head_sha: str) -> None:
        snapshots = self.session.scalars(
            select(RepositorySnapshot).where(
                RepositorySnapshot.project_id == project_id,
                RepositorySnapshot.ref == ref,
                RepositorySnapshot.status == "ready",
                RepositorySnapshot.head_sha != new_head_sha,
            )
        ).all()
        for snapshot in snapshots:
            snapshot.status = "stale"
        self.session.flush()

    def build_fingerprint(
        self,
        *,
        project_id: int,
        platform_type: str,
        repo_url: str | None,
        ref: str,
        head_sha: str,
        tool_signature: str,
        settings_hash: str,
    ) -> str:
        payload = {
            "project_id": project_id,
            "platform_type": platform_type,
            "repo_url": repo_url,
            "ref": ref,
            "head_sha": head_sha,
            "tool_signature": tool_signature,
            "settings_hash": settings_hash,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _build_indexed_paths(file_tree: list[dict[str, Any]]) -> list[str]:
        indexed_paths: list[str] = []
        for item in file_tree:
            if item.get("type") != "file":
                continue
            path = str(item.get("path", "")).strip()
            if path:
                indexed_paths.append(path)
        return indexed_paths

    @staticmethod
    def _settings_hash(settings: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(settings or {}, sort_keys=True).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _tool_signature() -> str:
        payload = {
            name: spec.schema
            for name, spec in sorted(READ_ONLY_TOOL_SPECS.items())
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
