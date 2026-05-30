from __future__ import annotations

from typing import Any

from app.integrations.base import BaseIntegrationAdapter, NormalizedWebhookEvent


class GitLabIntegrationAdapter(BaseIntegrationAdapter):
    platform_type = "gitlab"

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
                author=self._get_text(self._get_dict(payload, "user"), "name") or self._get_text(payload, "user_name"),
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
                author=self._get_text(self._get_dict(payload, "user"), "name") or self._get_text(payload, "user_name"),
                title=None,
                branch=self._parse_ref_branch(self._get_text(payload, "ref")),
                source_branch=None,
                target_branch=None,
                repo_url=self._get_text(project, "web_url") or self._get_text(self._get_dict(payload, "repository"), "homepage"),
                repo_full_name=self._get_text(project, "path_with_namespace"),
                external_project_id=self._to_optional_str(payload.get("project_id") or project.get("id")),
                external_event_id=event_uuid,
                last_commit_id=last_commit_id,
                webhook_data=payload,
            )

        raise ValueError(f"Unsupported GitLab webhook event: {object_kind!r}")

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
