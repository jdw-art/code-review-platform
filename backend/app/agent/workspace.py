from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkspaceContext:
    project_id: int
    project_name: str
    platform_type: str
    repo_url: str | None
    ref: str
    head_sha: str
    fingerprint: str
    overview: dict[str, Any]
    recent_commits: list[dict[str, Any]]

    def text(self) -> str:
        readme = str(self.overview.get("readme", "")).strip() or "none"
        commits = self.recent_commits or []
        commit_lines = "\n".join(
            f"- {item.get('id', '')} {item.get('message', '')}".strip()
            for item in commits
        ) or "- none"
        return (
            "Workspace:\n"
            f"- project_id: {self.project_id}\n"
            f"- project_name: {self.project_name}\n"
            f"- platform_type: {self.platform_type}\n"
            f"- repo_url: {self.repo_url or '-'}\n"
            f"- ref: {self.ref}\n"
            f"- head_sha: {self.head_sha}\n"
            f"- fingerprint: {self.fingerprint}\n"
            f"- readme:\n{readme}\n"
            f"- recent_commits:\n{commit_lines}"
        )

    @classmethod
    def build_fingerprint(cls, payload: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
