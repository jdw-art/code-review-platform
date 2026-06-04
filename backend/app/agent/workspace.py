from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, TypedDict


class NumberedFileSummary(TypedDict):
    path: str
    content: str
    start: int
    end: int
    total_lines: int
    file_version: str


class FileTreeEntrySummary(TypedDict):
    path: str
    type: str
    file_version: str


class FileTreeSummary(TypedDict):
    path: str
    entries: list[str]
    files: dict[str, FileTreeEntrySummary]


@dataclass(slots=True)
class WorkspaceSnapshot:
    project_id: str
    platform_type: str
    branch: str
    head_sha: str
    default_branch: str
    snapshot_digest: str
    project_docs_summary: dict[str, NumberedFileSummary]
    recent_commits_summary: list[str]
    file_tree_summary: FileTreeSummary


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_workspace_project_id(project_id: Any) -> str:
    normalized = str(project_id).strip()
    if not normalized:
        raise ValueError("Missing project id for workspace snapshot")
    return normalized


def _normalize_workspace_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "project_id" in normalized and normalized["project_id"] is not None:
        normalized["project_id"] = normalize_workspace_project_id(normalized["project_id"])
    return normalized


def build_workspace_fingerprint(snapshot: WorkspaceSnapshot | Mapping[str, Any]) -> str:
    payload = asdict(snapshot) if isinstance(snapshot, WorkspaceSnapshot) else dict(snapshot)
    payload = _normalize_workspace_payload(payload)
    return _stable_hash(payload)


def build_runtime_identity_hash(identity: Mapping[str, Any]) -> str:
    return _stable_hash(dict(identity))
