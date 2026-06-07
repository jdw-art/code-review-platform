from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.core.env_compat import load_backend_env_compat
from app.db.models import ReviewRecord
from app.integrations.base import BaseIntegrationAdapter, NormalizedWebhookEvent


class GitHubIntegrationAdapter(BaseIntegrationAdapter):
    platform_type = "github"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        load_backend_env_compat()
        self.access_token = access_token or os.getenv("GITHUB_ACCESS_TOKEN")
        self.base_url = base_url or os.getenv("GITHUB_URL")
        self.api_base_url = api_base_url or os.getenv("GITHUB_API_URL")

    def parse_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedWebhookEvent:
        normalized_headers = self.normalize_headers(headers)
        event_name = normalized_headers.get("x-github-event")
        delivery_id = normalized_headers.get("x-github-delivery")

        if not event_name:
            raise ValueError("Missing GitHub webhook event header")

        if event_name == "pull_request":
            repository = self._get_dict(payload, "repository")
            pull_request = self._get_dict(payload, "pull_request")
            head = self._get_dict(pull_request, "head")
            base = self._get_dict(pull_request, "base")
            pull_request_user = self._get_dict(pull_request, "user")
            return NormalizedWebhookEvent(
                platform_type=self.platform_type,
                event_type="pull_request",
                action=self._get_text(payload, "action"),
                author=self._get_text(pull_request_user, "login")
                or self._get_text(self._get_dict(payload, "sender"), "login"),
                title=self._get_text(pull_request, "title"),
                branch=None,
                source_branch=self._get_text(head, "ref"),
                target_branch=self._get_text(base, "ref"),
                repo_url=self._get_text(repository, "html_url"),
                repo_full_name=self._get_text(repository, "full_name"),
                external_project_id=self._to_optional_str(repository.get("id")),
                external_event_id=self._to_optional_str(delivery_id),
                last_commit_id=self._to_optional_str(head.get("sha")),
                webhook_data=payload,
            )

        if event_name == "push":
            repository = self._get_dict(payload, "repository")
            head_commit = self._get_dict(payload, "head_commit")
            last_commit_id = self._to_optional_str(head_commit.get("id") or payload.get("after"))
            return NormalizedWebhookEvent(
                platform_type=self.platform_type,
                event_type="push",
                action="push",
                author=self._get_text(self._get_dict(payload, "sender"), "login"),
                title=self._get_text(head_commit, "message"),
                branch=self._parse_ref_branch(self._get_text(payload, "ref")),
                source_branch=None,
                target_branch=None,
                repo_url=self._get_text(repository, "html_url"),
                repo_full_name=self._get_text(repository, "full_name"),
                external_project_id=self._to_optional_str(repository.get("id")),
                external_event_id=self._to_optional_str(delivery_id),
                last_commit_id=last_commit_id,
                webhook_data=payload,
            )

        raise ValueError(f"Unsupported GitHub webhook event: {event_name!r}")

    def fetch_changes(self, record: ReviewRecord) -> list[dict[str, Any]]:
        repo_full_name = self._require_repo_full_name(record)

        if record.event_type == "pull_request":
            pull_request_id = self._require_pull_request_id(record)
            data = self._request_json(
                f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/pulls/{pull_request_id}/files"
            )
            return self._normalize_pull_request_files(data)

        if record.event_type == "push":
            before = self._optional_text(record.webhook_data.get("before"))
            after = self._optional_text(record.webhook_data.get("after")) or record.last_commit_id
            if not after or record.webhook_data.get("deleted") is True:
                return []
            if self._is_initial_push_before_sha(before):
                data = self._request_json(
                    f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/commits/{after}"
                )
                if not isinstance(data, dict):
                    return []
                return self._normalize_pull_request_files(data.get("files"))
            if before:
                data = self._request_json(
                    f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/compare/{before}...{after}"
                )
                return self._normalize_pull_request_files(data.get("files"))

        return []

    def fetch_commits(self, record: ReviewRecord) -> list[dict[str, Any]]:
        repo_full_name = self._require_repo_full_name(record)

        if record.event_type == "pull_request":
            pull_request_id = self._require_pull_request_id(record)
            data = self._request_json(
                f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/pulls/{pull_request_id}/commits"
            )
            if not isinstance(data, list):
                return []
            normalized: list[dict[str, Any]] = []
            for commit in data:
                if not isinstance(commit, dict):
                    continue
                commit_info = self._get_dict(commit, "commit")
                author_info = self._get_dict(commit_info, "author")
                message = self._optional_text(commit_info.get("message"))
                normalized.append(
                    {
                        "id": self._optional_text(commit.get("sha")),
                        "title": message.split("\n")[0] if message else None,
                        "message": message,
                        "author_name": self._optional_text(author_info.get("name")),
                        "author_email": self._optional_text(author_info.get("email")),
                        "created_at": self._optional_text(author_info.get("date")),
                        "web_url": self._optional_text(commit.get("html_url")),
                    }
                )
            return normalized

        if record.event_type == "push":
            commits = record.webhook_data.get("commits")
            if not isinstance(commits, list):
                return []
            normalized_commits: list[dict[str, Any]] = []
            for commit in commits:
                if not isinstance(commit, dict):
                    continue
                normalized_commits.append(
                    {
                        "id": self._optional_text(commit.get("id")),
                        "message": self._optional_text(commit.get("message")),
                        "author": self._optional_text(self._get_dict(commit, "author").get("name")),
                        "timestamp": self._optional_text(commit.get("timestamp")),
                        "url": self._optional_text(commit.get("url")),
                    }
                )
            return normalized_commits

        return []

    def publish_review_comment(self, *, record: ReviewRecord, review_result: str) -> None:
        repo_full_name = self._require_repo_full_name(record)

        if record.event_type == "pull_request":
            pull_request_id = self._require_pull_request_id(record)
            self._request_json(
                f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/issues/{pull_request_id}/comments",
                method="POST",
                payload={"body": review_result},
            )
            return

        commit_id = self._optional_text(record.last_commit_id)
        if not commit_id:
            raise ValueError("Missing commit id for GitHub push review comment")
        self._request_json(
            f"{self._resolve_api_base_url(record)}/repos/{repo_full_name}/commits/{commit_id}/comments",
            method="POST",
            payload={"body": review_result},
        )

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        token = self._require_access_token()
        request = Request(
            url,
            method=method,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)

    def _resolve_api_base_url(self, record: ReviewRecord) -> str:
        if self.api_base_url:
            return self.api_base_url.rstrip("/")

        parsed = urlsplit(self.base_url or record.url or "")
        if not parsed.scheme or not parsed.netloc:
            repository = self._get_dict(record.webhook_data, "repository")
            parsed = urlsplit(self._optional_text(repository.get("html_url")) or "")
        if parsed.hostname == "github.com":
            return "https://api.github.com"
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/api/v3"
        return "https://api.github.com"

    def _require_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        raise ValueError("Missing GitHub access token")

    @staticmethod
    def _is_initial_push_before_sha(before: str | None) -> bool:
        return bool(before) and set(before) == {"0"}

    @staticmethod
    def _require_repo_full_name(record: ReviewRecord) -> str:
        repository = GitHubIntegrationAdapter._get_dict(record.webhook_data, "repository")
        repo_full_name = GitHubIntegrationAdapter._optional_text(repository.get("full_name"))
        if repo_full_name:
            return repo_full_name
        raise ValueError("Missing GitHub repository full name")

    @staticmethod
    def _require_pull_request_id(record: ReviewRecord) -> str:
        pull_request = GitHubIntegrationAdapter._get_dict(record.webhook_data, "pull_request")
        pull_request_id = GitHubIntegrationAdapter._optional_text(
            record.external_pull_request_id or pull_request.get("number") or pull_request.get("id")
        )
        if pull_request_id:
            return pull_request_id
        raise ValueError("Missing GitHub pull request id")

    @classmethod
    def _normalize_pull_request_files(cls, files: Any) -> list[dict[str, Any]]:
        if not isinstance(files, list):
            return []
        normalized: list[dict[str, Any]] = []
        for file in files:
            if not isinstance(file, dict):
                continue
            filename = cls._optional_text(file.get("filename"))
            if not filename:
                continue
            normalized.append(
                {
                    "old_path": filename,
                    "new_path": filename,
                    "diff": cls._optional_text(file.get("patch")) or "",
                    "status": cls._optional_text(file.get("status")) or "",
                    "additions": int(file.get("additions", 0) or 0),
                    "deletions": int(file.get("deletions", 0) or 0),
                }
            )
        return normalized

    @staticmethod
    def _parse_ref_branch(ref: str | None) -> str | None:
        if not ref:
            return None
        return ref.removeprefix("refs/heads/")

    @staticmethod
    def _get_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
        value = payload.get(key)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _get_text(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) and value != "" else None

    @staticmethod
    def _to_optional_str(value: Any) -> str | None:
        if value is None or value == "":
            return None
        return str(value)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
