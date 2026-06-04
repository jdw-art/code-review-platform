from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from app.core.env_compat import load_backend_env_compat
from app.db.models import ReviewRecord
from app.integrations.base import BaseIntegrationAdapter, NormalizedWebhookEvent


class GitLabIntegrationAdapter(BaseIntegrationAdapter):
    platform_type = "gitlab"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        load_backend_env_compat()
        self.access_token = access_token or os.getenv("GITLAB_ACCESS_TOKEN")
        self.base_url = base_url or os.getenv("GITLAB_URL")

    def parse_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedWebhookEvent:
        normalized_headers = self.normalize_headers(headers)
        object_kind = self._get_text(payload, "object_kind") or self._get_text(payload, "event_name")
        event_uuid = self._to_optional_str(normalized_headers.get("x-gitlab-event-uuid"))

        if object_kind == "merge_request":
            attributes = self._get_dict(payload, "object_attributes")
            project = self._get_dict(payload, "project")
            last_commit = self._get_dict(attributes, "last_commit")
            return NormalizedWebhookEvent(
                platform_type=self.platform_type,
                event_type="merge_request",
                action=self._get_text(attributes, "action"),
                author=self._get_text(self._get_dict(payload, "user"), "name")
                or self._get_text(payload, "user_name"),
                title=self._get_text(attributes, "title"),
                branch=None,
                source_branch=self._get_text(attributes, "source_branch"),
                target_branch=self._get_text(attributes, "target_branch"),
                repo_url=self._get_text(project, "web_url"),
                repo_full_name=self._get_text(project, "path_with_namespace"),
                external_project_id=self._to_optional_str(project.get("id") or payload.get("project_id")),
                external_event_id=event_uuid,
                last_commit_id=self._to_optional_str(last_commit.get("id") or attributes.get("last_commit_id")),
                webhook_data=payload,
            )

        if object_kind == "push":
            project = self._get_dict(payload, "project")
            last_commit_id = self._to_optional_str(payload.get("checkout_sha") or payload.get("after"))
            return NormalizedWebhookEvent(
                platform_type=self.platform_type,
                event_type="push",
                action="push",
                author=self._get_text(self._get_dict(payload, "user"), "name")
                or self._get_text(payload, "user_name"),
                title=None,
                branch=self._parse_ref_branch(self._get_text(payload, "ref")),
                source_branch=None,
                target_branch=None,
                repo_url=self._get_text(project, "web_url")
                or self._get_text(self._get_dict(payload, "repository"), "homepage"),
                repo_full_name=self._get_text(project, "path_with_namespace"),
                external_project_id=self._to_optional_str(payload.get("project_id") or project.get("id")),
                external_event_id=event_uuid,
                last_commit_id=last_commit_id,
                webhook_data=payload,
            )

        raise ValueError(f"Unsupported GitLab webhook event: {object_kind!r}")

    def fetch_changes(self, record: ReviewRecord) -> list[dict[str, Any]]:
        project_id = self._require_project_id(record)

        if record.event_type == "merge_request":
            merge_request_id = self._require_merge_request_id(record)
            data = self._request_json(
                self._build_api_url(
                    record,
                    f"/api/v4/projects/{quote(project_id, safe='')}/merge_requests/{quote(merge_request_id, safe='')}/changes",
                    {"access_raw_diffs": "true"},
                )
            )
            changes = data.get("changes")
            return changes if isinstance(changes, list) else []

        if record.event_type == "push":
            before = self._optional_text(record.webhook_data.get("before"))
            after = self._optional_text(record.webhook_data.get("after")) or record.last_commit_id
            if not after or after.startswith("0000000"):
                return []
            if before and not before.startswith("0000000"):
                data = self._request_json(
                    self._build_api_url(
                        record,
                        f"/api/v4/projects/{quote(project_id, safe='')}/repository/compare",
                        {"from": before, "to": after},
                    )
                )
                diffs = data.get("diffs")
                return diffs if isinstance(diffs, list) else []

            data = self._request_json(
                self._build_api_url(
                    record,
                    f"/api/v4/projects/{quote(project_id, safe='')}/repository/commits/{quote(after, safe='')}/diff",
                )
            )
            return data if isinstance(data, list) else []

        return []

    def fetch_commits(self, record: ReviewRecord) -> list[dict[str, Any]]:
        if record.event_type == "merge_request":
            project_id = self._require_project_id(record)
            merge_request_id = self._require_merge_request_id(record)
            data = self._request_json(
                self._build_api_url(
                    record,
                    f"/api/v4/projects/{quote(project_id, safe='')}/merge_requests/{quote(merge_request_id, safe='')}/commits",
                )
            )
            return data if isinstance(data, list) else []

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
        project_id = self._require_project_id(record)

        if record.event_type == "merge_request":
            merge_request_id = self._require_merge_request_id(record)
            self._request_json(
                self._build_api_url(
                    record,
                    f"/api/v4/projects/{quote(project_id, safe='')}/merge_requests/{quote(merge_request_id, safe='')}/notes",
                ),
                method="POST",
                payload={"body": review_result},
            )
            return

        commit_id = self._optional_text(record.last_commit_id)
        if not commit_id:
            raise ValueError("Missing commit id for GitLab push review comment")
        self._request_json(
            self._build_api_url(
                record,
                f"/api/v4/projects/{quote(project_id, safe='')}/repository/commits/{quote(commit_id, safe='')}/comments",
            ),
            method="POST",
            payload={"note": review_result},
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
                "Private-Token": token,
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)

    def _build_api_url(
        self,
        record: ReviewRecord,
        path: str,
        query: dict[str, str] | None = None,
    ) -> str:
        base_url = self._resolve_base_url(record).rstrip("/")
        if not query:
            return f"{base_url}{path}"
        return f"{base_url}{path}?{urlencode(query)}"

    def _resolve_base_url(self, record: ReviewRecord) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if record.url:
            parsed = urlsplit(record.url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        project = self._get_dict(record.webhook_data, "project")
        web_url = self._optional_text(project.get("web_url"))
        if web_url:
            parsed = urlsplit(web_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        raise ValueError("Missing GitLab base URL")

    def _require_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        raise ValueError("Missing GitLab access token")

    @staticmethod
    def _require_project_id(record: ReviewRecord) -> str:
        project_id = GitLabIntegrationAdapter._optional_text(
            record.external_project_id
            or GitLabIntegrationAdapter._get_dict(record.webhook_data, "project").get("id")
            or record.webhook_data.get("project_id")
        )
        if project_id:
            return project_id
        raise ValueError("Missing GitLab project id")

    @staticmethod
    def _require_merge_request_id(record: ReviewRecord) -> str:
        attributes = GitLabIntegrationAdapter._get_dict(record.webhook_data, "object_attributes")
        merge_request_id = GitLabIntegrationAdapter._optional_text(
            record.external_merge_request_id or attributes.get("iid") or attributes.get("id")
        )
        if merge_request_id:
            return merge_request_id
        raise ValueError("Missing GitLab merge request id")

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
