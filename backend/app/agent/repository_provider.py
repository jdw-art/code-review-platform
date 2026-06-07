from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from app.db.models import Project
from app.integrations.github import GitHubIntegrationAdapter
from app.integrations.gitlab import GitLabIntegrationAdapter


class RepositoryProvider(Protocol):
    def resolve_branch_head(self, *, branch: str) -> str: ...

    def list_tree(
        self,
        *,
        branch: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]: ...

    def read_file(
        self,
        *,
        branch: str,
        path: str,
        start: int,
        end: int,
        ref: str | None = None,
    ) -> dict[str, object]: ...

    def search_code(
        self,
        *,
        branch: str,
        query: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]: ...

    def get_recent_commits(
        self,
        *,
        branch: str,
        limit: int = 5,
        ref: str | None = None,
    ) -> list[str]: ...

    def get_change_summary(self, *, external_id: str) -> dict[str, object]: ...

    def list_commits(self, *, external_id: str) -> list[dict[str, object]]: ...

    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]: ...

    def get_diff_overview(self, *, external_id: str) -> dict[str, object]: ...


def _normalize_path(path: str) -> str:
    normalized = path.strip().strip("/")
    return normalized if normalized not in {"", "."} else "."


def _matches_scope(candidate: str, scope: str) -> bool:
    if scope == ".":
        return True
    return candidate == scope or candidate.startswith(f"{scope}/")


def _line_window(text: str, *, start: int, end: int) -> tuple[str, int, int, int]:
    lines = text.splitlines()
    total_lines = len(lines)
    window_start = max(start, 1)
    window_end = max(window_start, end)
    sliced = lines[window_start - 1 : window_end]
    if total_lines == 0:
        return "", 1, 1, 0
    if not sliced:
        clamped = min(window_start, total_lines)
        return "", clamped, clamped, total_lines
    content = "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(sliced, start=window_start)
    )
    return content, window_start, min(window_end, total_lines), total_lines


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RepositoryContentDecodeError(ValueError):
    """Raised when repository content cannot be decoded as UTF-8 text."""


class RepositoryPaginationError(ValueError):
    """Raised when a paginated repository endpoint returns an unexpected payload."""


def _format_commit_summary(commit_id: str | None, message: str | None) -> str | None:
    normalized_id = str(commit_id or "").strip()
    normalized_message = str(message or "").strip()
    if not normalized_id and not normalized_message:
        return None
    short_id = normalized_id[:7] if normalized_id else "unknown"
    title = normalized_message.splitlines()[0] if normalized_message else ""
    return f"{short_id} {title}".strip()


@dataclass(slots=True)
class FakeRepositoryProvider:
    branch_heads: dict[str, str]
    files: dict[tuple[str, str], str]
    recent_commits: dict[str, list[str]] = field(default_factory=dict)
    change_summaries: dict[str, dict[str, object]] = field(default_factory=dict)
    commit_lists: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    comment_threads: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    diff_overviews: dict[str, dict[str, object]] = field(default_factory=dict)

    def resolve_branch_head(self, *, branch: str) -> str:
        return self.branch_heads[branch]

    def list_tree(
        self,
        *,
        branch: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]:
        del ref
        scope = _normalize_path(path)
        branch_files = {
            file_path: {
                "path": file_path,
                "type": "blob",
                "file_version": _hash_text(text),
            }
            for (file_branch, file_path), text in self.files.items()
            if file_branch == branch and _matches_scope(file_path, scope)
        }
        return {
            "path": scope,
            "entries": sorted(branch_files),
            "files": branch_files,
        }

    def read_file(
        self,
        *,
        branch: str,
        path: str,
        start: int,
        end: int,
        ref: str | None = None,
    ) -> dict[str, object]:
        del ref
        text = self.files[(branch, path)]
        content, window_start, window_end, total_lines = _line_window(
            text,
            start=start,
            end=end,
        )
        return {
            "path": path,
            "content": content,
            "start": window_start,
            "end": window_end,
            "total_lines": total_lines,
            "file_version": _hash_text(text),
        }

    def search_code(
        self,
        *,
        branch: str,
        query: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]:
        del ref
        scope = _normalize_path(path)
        lowered_query = query.lower()
        matches: list[dict[str, object]] = []
        for (file_branch, file_path), text in sorted(self.files.items()):
            if file_branch != branch or not _matches_scope(file_path, scope):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if lowered_query in line.lower():
                    matches.append(
                        {
                            "path": file_path,
                            "line": line_number,
                            "text": line,
                        }
                    )
        return {"matches": matches}

    def get_recent_commits(
        self,
        *,
        branch: str,
        limit: int = 5,
        ref: str | None = None,
    ) -> list[str]:
        del ref
        return self.recent_commits.get(branch, [])[:limit]

    def get_change_summary(self, *, external_id: str) -> dict[str, object]:
        return self.change_summaries.get(
            external_id,
            {
                "external_id": external_id,
                "title": f"Change {external_id}",
            },
        )

    def list_commits(self, *, external_id: str) -> list[dict[str, object]]:
        return self.commit_lists.get(external_id, [])

    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]:
        return self.comment_threads.get(external_id, [])

    def get_diff_overview(self, *, external_id: str) -> dict[str, object]:
        return self.diff_overviews.get(
            external_id,
            {
                "external_id": external_id,
                "files_changed": 0,
                "additions": 0,
                "deletions": 0,
            },
        )


class _BaseRemoteRepositoryProvider:
    def __init__(self, *, project: Project) -> None:
        self.project = project

    def search_code(
        self,
        *,
        branch: str,
        query: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]:
        resolved_ref = ref or self.resolve_branch_head(branch=branch)
        scope = _normalize_path(path)
        lowered_query = query.lower()
        tree = self.list_tree(branch=branch, path=scope, ref=resolved_ref)
        matches: list[dict[str, object]] = []
        for file_path, metadata in tree.get("files", {}).items():
            if not isinstance(metadata, dict) or metadata.get("type") != "blob":
                continue
            try:
                file_payload = self.read_file(
                    branch=branch,
                    path=file_path,
                    start=1,
                    end=2_147_483_647,
                    ref=resolved_ref,
                )
            except RepositoryContentDecodeError:
                continue
            for numbered_line in str(file_payload.get("content", "")).splitlines():
                prefix, separator, text = numbered_line.partition(": ")
                if separator != ": ":
                    continue
                if lowered_query not in text.lower():
                    continue
                try:
                    line_number = int(prefix)
                except ValueError:
                    continue
                matches.append(
                    {
                        "path": file_path,
                        "line": line_number,
                        "text": text,
                    }
                )
        return {"matches": matches}

    def _request_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        request = Request(
            url,
            method=method,
            headers=headers,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
        if not body:
            return None
        return json.loads(body)

    def _request_text(self, url: str, *, headers: dict[str, str]) -> str:
        request = Request(url, method="GET", headers=headers)
        with urlopen(request, timeout=10) as response:
            body = response.read()
        if not body:
            return ""
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RepositoryContentDecodeError("Repository content is not valid UTF-8") from exc

    def _request_paginated_list(
        self,
        *,
        build_url: Callable[[int, int], str],
        headers: dict[str, str],
        per_page: int = 100,
    ) -> list[Any]:
        items: list[Any] = []
        page = 1
        while True:
            payload = self._request_json(build_url(page, per_page), headers=headers)
            if not isinstance(payload, list):
                raise RepositoryPaginationError(
                    f"Unexpected paginated payload on page {page}: {type(payload).__name__}"
                )
            if not payload:
                break
            items.extend(payload)
            if len(payload) < per_page:
                break
            page += 1
        return items


class GitHubRepositoryProvider(_BaseRemoteRepositoryProvider):
    def __init__(
        self,
        *,
        project: Project,
        access_token: str | None = None,
        base_url: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        super().__init__(project=project)
        self.adapter = GitHubIntegrationAdapter(
            access_token=access_token,
            base_url=base_url,
            api_base_url=api_base_url,
        )

    def resolve_branch_head(self, *, branch: str) -> str:
        payload = self._request_json(
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/branches/{quote(branch, safe='')}",
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitHub branch payload")
        commit = payload.get("commit")
        if isinstance(commit, dict) and commit.get("sha"):
            return str(commit["sha"])
        raise ValueError("Missing GitHub branch head sha")

    def list_tree(
        self,
        *,
        branch: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]:
        scope = _normalize_path(path)
        resolved_ref = ref or self.resolve_branch_head(branch=branch)
        payload = self._request_json(
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/git/trees/{quote(resolved_ref, safe='')}?recursive=1",
            headers=self._headers(),
        )
        if isinstance(payload, dict) and payload.get("truncated") is True:
            return self._list_tree_from_contents(branch=branch, path=scope, ref=resolved_ref)
        tree = payload.get("tree") if isinstance(payload, dict) else None
        if not isinstance(tree, list):
            return {"path": scope, "entries": [], "files": {}}

        files: dict[str, dict[str, object]] = {}
        for entry in tree:
            if not isinstance(entry, dict):
                continue
            entry_path = str(entry.get("path") or "").strip("/")
            if not entry_path or not _matches_scope(entry_path, scope):
                continue
            files[entry_path] = {
                "path": entry_path,
                "type": str(entry.get("type") or "blob"),
                "file_version": str(entry.get("sha") or ""),
            }
        return {
            "path": scope,
            "entries": sorted(files),
            "files": files,
        }

    def read_file(
        self,
        *,
        branch: str,
        path: str,
        start: int,
        end: int,
        ref: str | None = None,
    ) -> dict[str, object]:
        encoded_path = quote(path, safe="")
        payload = self._request_json(
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/contents/{encoded_path}?{urlencode({'ref': ref or branch})}",
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitHub file payload")
        content = self._decode_github_content(payload)
        file_version = str(payload.get("sha") or _hash_text(content))
        numbered_content, window_start, window_end, total_lines = _line_window(
            content,
            start=start,
            end=end,
        )
        return {
            "path": path,
            "content": numbered_content,
            "start": window_start,
            "end": window_end,
            "total_lines": total_lines,
            "file_version": file_version,
        }

    def get_recent_commits(
        self,
        *,
        branch: str,
        limit: int = 5,
        ref: str | None = None,
    ) -> list[str]:
        query = urlencode({"sha": ref or branch, "per_page": str(limit)})
        payload = self._request_json(
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/commits?{query}",
            headers=self._headers(),
        )
        if not isinstance(payload, list):
            return []
        summaries: list[str] = []
        for commit in payload:
            if not isinstance(commit, dict):
                continue
            commit_info = commit.get("commit")
            message = commit_info.get("message") if isinstance(commit_info, dict) else None
            summary = _format_commit_summary(commit.get("sha"), message)
            if summary:
                summaries.append(summary)
        return summaries

    def get_change_summary(self, *, external_id: str) -> dict[str, object]:
        payload = self._request_json(
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/pulls/{quote(str(external_id), safe='')}",
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            return {"external_id": str(external_id)}
        head = payload.get("head") if isinstance(payload.get("head"), dict) else {}
        base = payload.get("base") if isinstance(payload.get("base"), dict) else {}
        user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
        return {
            "external_id": str(external_id),
            "title": payload.get("title"),
            "state": payload.get("state"),
            "url": payload.get("html_url"),
            "author": user.get("login"),
            "source_branch": head.get("ref"),
            "target_branch": base.get("ref"),
            "head_sha": head.get("sha"),
            "base_sha": base.get("sha"),
        }

    def list_commits(self, *, external_id: str) -> list[dict[str, object]]:
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: (
                f"{self._api_base_url()}/repos/{self._repo_full_name()}/pulls/"
                f"{quote(str(external_id), safe='')}/commits?{urlencode({'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )
        commits: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            commit_info = item.get("commit") if isinstance(item.get("commit"), dict) else {}
            commits.append(
                {
                    "id": item.get("sha"),
                    "message": commit_info.get("message"),
                    "title": str(commit_info.get("message") or "").splitlines()[0] or None,
                    "url": item.get("html_url"),
                }
            )
        return commits

    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]:
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: (
                f"{self._api_base_url()}/repos/{self._repo_full_name()}/pulls/"
                f"{quote(str(external_id), safe='')}/comments?{urlencode({'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )
        threads_by_id: dict[object, dict[str, object]] = {}
        thread_order: list[object] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            user = item.get("user") if isinstance(item.get("user"), dict) else {}
            line = item.get("line")
            if line is None:
                line = item.get("original_line")
            thread_id = item.get("in_reply_to_id") or item.get("id")
            note = {
                "id": item.get("id"),
                "body": item.get("body"),
                "author": user.get("login"),
                "created_at": item.get("created_at"),
                "path": item.get("path"),
                "line": line,
                "start_line": item.get("start_line"),
                "side": item.get("side"),
                "resolved": item.get("resolved"),
            }
            if thread_id not in threads_by_id:
                threads_by_id[thread_id] = {
                    "id": thread_id,
                    "body": note["body"],
                    "author": note["author"],
                    "created_at": note["created_at"],
                    "path": note["path"],
                    "line": note["line"],
                    "start_line": note["start_line"],
                    "resolved": note["resolved"],
                    "notes": [note],
                }
                thread_order.append(thread_id)
                continue
            thread = threads_by_id[thread_id]
            notes = thread.get("notes")
            if isinstance(notes, list):
                notes.append(note)
            if item.get("in_reply_to_id") is None:
                thread.update(
                    {
                        "body": note["body"],
                        "author": note["author"],
                        "created_at": note["created_at"],
                        "path": note["path"],
                        "line": note["line"],
                        "start_line": note["start_line"],
                    }
                )
        return [threads_by_id[thread_id] for thread_id in thread_order]

    def get_diff_overview(self, *, external_id: str) -> dict[str, object]:
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: (
                f"{self._api_base_url()}/repos/{self._repo_full_name()}/pulls/"
                f"{quote(str(external_id), safe='')}/files?{urlencode({'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )
        additions = 0
        deletions = 0
        files_changed = 0
        files: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            files_changed += 1
            additions += int(item.get("additions") or 0)
            deletions += int(item.get("deletions") or 0)
            files.append(
                {
                    "path": item.get("filename"),
                    "status": item.get("status"),
                    "additions": item.get("additions"),
                    "deletions": item.get("deletions"),
                }
            )
        return {
            "external_id": str(external_id),
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,
            "files": files,
        }

    def _list_tree_from_contents(self, *, branch: str, path: str, ref: str | None = None) -> dict[str, object]:
        scope = _normalize_path(path)
        files: dict[str, dict[str, object]] = {}
        start_path = "" if scope == "." else scope
        for item in self._walk_contents(branch=branch, path=start_path, ref=ref):
            entry_path = str(item.get("path") or "").strip("/")
            if not entry_path or not _matches_scope(entry_path, scope):
                continue
            files[entry_path] = {
                "path": entry_path,
                "type": "blob",
                "file_version": str(item.get("sha") or ""),
            }
        return {
            "path": scope,
            "entries": sorted(files),
            "files": files,
        }

    def _walk_contents(self, *, branch: str, path: str, ref: str | None = None) -> list[dict[str, object]]:
        query = urlencode({"ref": ref or branch})
        encoded_path = quote(path, safe="")
        url = (
            f"{self._api_base_url()}/repos/{self._repo_full_name()}/contents?{query}"
            if not encoded_path
            else f"{self._api_base_url()}/repos/{self._repo_full_name()}/contents/{encoded_path}?{query}"
        )
        payload = self._request_json(url, headers=self._headers())
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            return []
        files: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "")
            if item_type == "dir":
                nested_path = str(item.get("path") or "").strip("/")
                if nested_path:
                    files.extend(self._walk_contents(branch=branch, path=nested_path, ref=ref))
                continue
            if item_type == "file":
                files.append(item)
        return files

    def _repo_full_name(self) -> str:
        configured = str(self.project.settings.get("external_repo_full_name") or "").strip("/")
        if configured:
            return configured
        parsed = urlsplit(self.project.repo_url or "")
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if path:
            return path
        raise ValueError("Missing GitHub repository full name")

    def _api_base_url(self) -> str:
        if self.adapter.api_base_url:
            return self.adapter.api_base_url.rstrip("/")
        parsed = urlsplit(self.adapter.base_url or self.project.repo_url or "")
        if parsed.hostname == "github.com":
            return "https://api.github.com"
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/api/v3"
        return "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        token = self.adapter.access_token
        if not token:
            raise ValueError("Missing GitHub access token")
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _decode_github_content(payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if isinstance(content, str):
            encoded = content.encode("utf-8")
            try:
                if str(payload.get("encoding") or "").lower() == "base64":
                    return base64.b64decode(encoded, validate=False).decode("utf-8")
                return content
            except UnicodeDecodeError as exc:
                raise RepositoryContentDecodeError("GitHub file content is not valid UTF-8") from exc
        raise ValueError("Missing GitHub file content")


class GitLabRepositoryProvider(_BaseRemoteRepositoryProvider):
    def __init__(
        self,
        *,
        project: Project,
        access_token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(project=project)
        self.adapter = GitLabIntegrationAdapter(
            access_token=access_token,
            base_url=base_url,
        )

    def resolve_branch_head(self, *, branch: str) -> str:
        payload = self._request_json(
            self._api_url(f"/api/v4/projects/{self._project_ref()}/repository/branches/{quote(branch, safe='')}"),
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitLab branch payload")
        commit = payload.get("commit")
        if isinstance(commit, dict) and commit.get("id"):
            return str(commit["id"])
        raise ValueError("Missing GitLab branch head sha")

    def list_tree(
        self,
        *,
        branch: str,
        path: str = ".",
        ref: str | None = None,
    ) -> dict[str, object]:
        scope = _normalize_path(path)
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: self._api_url(
                "/api/v4/projects/"
                f"{self._project_ref()}/repository/tree?"
                f"{urlencode({'ref': ref or branch, 'recursive': 'true', 'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )

        files: dict[str, dict[str, object]] = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            entry_path = str(entry.get("path") or "").strip("/")
            if not entry_path or not _matches_scope(entry_path, scope):
                continue
            files[entry_path] = {
                "path": entry_path,
                "type": str(entry.get("type") or "blob"),
                "file_version": str(entry.get("id") or ""),
            }
        return {
            "path": scope,
            "entries": sorted(files),
            "files": files,
        }

    def read_file(
        self,
        *,
        branch: str,
        path: str,
        start: int,
        end: int,
        ref: str | None = None,
    ) -> dict[str, object]:
        encoded_path = quote(path, safe="")
        file_url = self._api_url(
            f"/api/v4/projects/{self._project_ref()}/repository/files/{encoded_path}?{urlencode({'ref': ref or branch})}"
        )
        payload = self._request_json(file_url, headers=self._headers())
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitLab file payload")

        if isinstance(payload.get("content"), str):
            raw_text = self._decode_gitlab_content(payload)
        else:
            raw_text = self._request_text(
                self._api_url(
                    f"/api/v4/projects/{self._project_ref()}/repository/files/{encoded_path}/raw?{urlencode({'ref': ref or branch})}"
                ),
                headers=self._headers(),
            )
        file_version = str(payload.get("blob_id") or payload.get("content_sha256") or _hash_text(raw_text))
        numbered_content, window_start, window_end, total_lines = _line_window(
            raw_text,
            start=start,
            end=end,
        )
        return {
            "path": path,
            "content": numbered_content,
            "start": window_start,
            "end": window_end,
            "total_lines": total_lines,
            "file_version": file_version,
        }

    def get_recent_commits(
        self,
        *,
        branch: str,
        limit: int = 5,
        ref: str | None = None,
    ) -> list[str]:
        query = urlencode({"ref_name": ref or branch, "per_page": str(limit)})
        payload = self._request_json(
            self._api_url(f"/api/v4/projects/{self._project_ref()}/repository/commits?{query}"),
            headers=self._headers(),
        )
        if not isinstance(payload, list):
            return []
        summaries: list[str] = []
        for commit in payload:
            if not isinstance(commit, dict):
                continue
            summary = _format_commit_summary(commit.get("id"), commit.get("title") or commit.get("message"))
            if summary:
                summaries.append(summary)
        return summaries

    def get_change_summary(self, *, external_id: str) -> dict[str, object]:
        payload = self._request_json(
            self._api_url(
                f"/api/v4/projects/{self._project_ref()}/merge_requests/{quote(str(external_id), safe='')}"
            ),
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            return {"external_id": str(external_id)}
        diff_refs = payload.get("diff_refs") if isinstance(payload.get("diff_refs"), dict) else {}
        author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
        return {
            "external_id": str(external_id),
            "title": payload.get("title"),
            "state": payload.get("state"),
            "url": payload.get("web_url"),
            "author": author.get("username") or author.get("name"),
            "source_branch": payload.get("source_branch"),
            "target_branch": payload.get("target_branch"),
            "head_sha": diff_refs.get("head_sha"),
            "base_sha": diff_refs.get("base_sha"),
        }

    def list_commits(self, *, external_id: str) -> list[dict[str, object]]:
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: self._api_url(
                "/api/v4/projects/"
                f"{self._project_ref()}/merge_requests/{quote(str(external_id), safe='')}/commits?"
                f"{urlencode({'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )
        commits: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            commits.append(
                {
                    "id": item.get("id"),
                    "message": item.get("message") or item.get("title"),
                    "title": item.get("title"),
                    "url": item.get("web_url"),
                }
            )
        return commits

    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]:
        payload = self._request_paginated_list(
            build_url=lambda page, per_page: self._api_url(
                "/api/v4/projects/"
                f"{self._project_ref()}/merge_requests/{quote(str(external_id), safe='')}/discussions?"
                f"{urlencode({'per_page': per_page, 'page': page})}"
            ),
            headers=self._headers(),
        )
        threads: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            note_payloads = item.get("notes") if isinstance(item.get("notes"), list) else []
            notes: list[dict[str, object]] = []
            for note in note_payloads:
                if not isinstance(note, dict):
                    continue
                author = note.get("author") if isinstance(note.get("author"), dict) else {}
                position = note.get("position") if isinstance(note.get("position"), dict) else {}
                path = position.get("new_path") or position.get("old_path")
                line = position.get("new_line")
                if line is None:
                    line = position.get("old_line")
                notes.append(
                    {
                        "id": note.get("id"),
                        "body": note.get("body"),
                        "author": author.get("username") or author.get("name"),
                        "created_at": note.get("created_at"),
                        "path": path,
                        "line": line,
                        "resolved": note.get("resolved"),
                    }
                )
            first_note = notes[0] if notes else {}
            resolved = item.get("resolved")
            if resolved is None and notes:
                resolved = notes[-1].get("resolved")
            threads.append(
                {
                    "id": item.get("id"),
                    "body": first_note.get("body"),
                    "author": first_note.get("author"),
                    "created_at": first_note.get("created_at"),
                    "path": first_note.get("path"),
                    "line": first_note.get("line"),
                    "resolved": resolved,
                    "notes": notes,
                }
            )
        return threads

    def get_diff_overview(self, *, external_id: str) -> dict[str, object]:
        payload = self._request_json(
            self._api_url(
                f"/api/v4/projects/{self._project_ref()}/merge_requests/{quote(str(external_id), safe='')}/changes"
            ),
            headers=self._headers(),
        )
        if not isinstance(payload, dict):
            return {"external_id": str(external_id), "files_changed": 0, "additions": 0, "deletions": 0}
        changes = payload.get("changes")
        if not isinstance(changes, list):
            changes = []
        files: list[dict[str, object]] = []
        for item in changes:
            if not isinstance(item, dict):
                continue
            diff_text = str(item.get("diff") or "")
            additions = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
            deletions = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
            files.append(
                {
                    "path": item.get("new_path") or item.get("old_path"),
                    "status": item.get("new_file")
                    and "added"
                    or item.get("deleted_file")
                    and "removed"
                    or "modified",
                    "additions": additions,
                    "deletions": deletions,
                }
            )
        return {
            "external_id": str(external_id),
            "files_changed": len(files),
            "additions": sum(int(item["additions"]) for item in files),
            "deletions": sum(int(item["deletions"]) for item in files),
            "files": files,
        }

    def _project_ref(self) -> str:
        project_id = str(self.project.settings.get("external_project_id") or "").strip()
        if project_id:
            return quote(project_id, safe="")
        project_path = str(self.project.settings.get("gitlab_project_path") or "").strip("/")
        if not project_path:
            parsed = urlsplit(self.project.repo_url or "")
            project_path = parsed.path.strip("/")
            if project_path.endswith(".git"):
                project_path = project_path[:-4]
        if project_path:
            return quote(project_path, safe="")
        raise ValueError("Missing GitLab project reference")

    def _base_url(self) -> str:
        if self.adapter.base_url:
            return self.adapter.base_url.rstrip("/")
        parsed = urlsplit(self.project.repo_url or "")
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        raise ValueError("Missing GitLab base URL")

    def _api_url(self, path: str) -> str:
        return f"{self._base_url()}{path}"

    def _headers(self) -> dict[str, str]:
        token = self.adapter.access_token
        if not token:
            raise ValueError("Missing GitLab access token")
        return {
            "Private-Token": token,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _decode_gitlab_content(payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("Missing GitLab file content")
        try:
            if str(payload.get("encoding") or "").lower() == "base64":
                return base64.b64decode(content.encode("utf-8"), validate=False).decode("utf-8")
            return content
        except UnicodeDecodeError as exc:
            raise RepositoryContentDecodeError("GitLab file content is not valid UTF-8") from exc
