from __future__ import annotations

from typing import Any

from app.integrations.base import BaseIntegrationAdapter, NormalizedWebhookEvent


class GitHubIntegrationAdapter(BaseIntegrationAdapter):
    platform_type = "github"

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
