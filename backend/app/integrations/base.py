from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal


PlatformType = Literal["gitlab", "github"]
EventType = Literal["push", "merge_request", "pull_request"]


@dataclass(slots=True)
class NormalizedWebhookEvent:
    platform_type: PlatformType
    event_type: EventType
    action: str | None
    author: str | None
    title: str | None
    branch: str | None
    source_branch: str | None
    target_branch: str | None
    repo_url: str | None
    repo_full_name: str | None
    external_project_id: str | None
    external_event_id: str | None
    last_commit_id: str | None
    webhook_data: dict[str, Any]


class BaseIntegrationAdapter(ABC):
    platform_type: PlatformType

    @staticmethod
    def normalize_headers(headers: dict[str, str] | None) -> dict[str, str]:
        if not headers:
            return {}
        return {key.lower(): value for key, value in headers.items()}

    @abstractmethod
    def parse_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedWebhookEvent:
        raise NotImplementedError

    def fetch_changes(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("Fetching changes is not implemented in Task 5.")

    def fetch_commits(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("Fetching commits is not implemented in Task 5.")

    def publish_review_comment(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Publishing review comments is not implemented in Task 5.")
