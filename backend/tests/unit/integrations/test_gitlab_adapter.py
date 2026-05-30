from __future__ import annotations

import pytest

from app.integrations.gitlab import GitLabIntegrationAdapter


def test_gitlab_adapter_normalizes_merge_request_event() -> None:
    payload = {
        "object_kind": "merge_request",
        "event_type": "merge_request",
        "user": {"name": "Alice"},
        "project": {
            "id": 123,
            "web_url": "https://gitlab.example.com/acme/payment-service",
            "path_with_namespace": "acme/payment-service",
        },
        "object_attributes": {
            "action": "open",
            "title": "Add review queue worker",
            "source_branch": "feature/review-queue",
            "target_branch": "main",
            "url": "https://gitlab.example.com/acme/payment-service/-/merge_requests/7",
            "iid": 7,
            "target_project_id": 999,
            "last_commit": {"id": "abc123def456"},
        },
    }

    event = GitLabIntegrationAdapter().parse_webhook(
        payload,
        headers={
            "X-Gitlab-Event": "Merge Request Hook",
            "X-Gitlab-Event-UUID": "gitlab-delivery-001",
        },
    )

    assert event.platform_type == "gitlab"
    assert event.event_type == "merge_request"
    assert event.action == "open"
    assert event.author == "Alice"
    assert event.title == "Add review queue worker"
    assert event.branch is None
    assert event.source_branch == "feature/review-queue"
    assert event.target_branch == "main"
    assert event.repo_url == "https://gitlab.example.com/acme/payment-service"
    assert event.repo_full_name == "acme/payment-service"
    assert event.external_project_id == "123"
    assert event.external_event_id == "gitlab-delivery-001"
    assert event.last_commit_id == "abc123def456"
    assert event.webhook_data == payload


def test_gitlab_adapter_normalizes_push_event() -> None:
    payload = {
        "object_kind": "push",
        "event_name": "push",
        "user_name": "Bob",
        "project_id": 456,
        "project": {
            "web_url": "https://gitlab.example.com/acme/billing-service",
            "path_with_namespace": "acme/billing-service",
        },
        "ref": "refs/heads/release/2026.05",
        "checkout_sha": "fedcba987654",
        "after": "fedcba987654",
    }

    event = GitLabIntegrationAdapter().parse_webhook(
        payload,
        headers={"X-Gitlab-Event": "Push Hook"},
    )

    assert event.platform_type == "gitlab"
    assert event.event_type == "push"
    assert event.action == "push"
    assert event.author == "Bob"
    assert event.title is None
    assert event.branch == "release/2026.05"
    assert event.source_branch is None
    assert event.target_branch is None
    assert event.repo_url == "https://gitlab.example.com/acme/billing-service"
    assert event.repo_full_name == "acme/billing-service"
    assert event.external_project_id == "456"
    assert event.external_event_id is None
    assert event.last_commit_id == "fedcba987654"
    assert event.webhook_data == payload


def test_gitlab_adapter_uses_none_external_event_id_when_event_uuid_header_missing() -> None:
    payload = {
        "object_kind": "merge_request",
        "user": {"name": "Alice"},
        "project": {
            "id": 123,
            "web_url": "https://gitlab.example.com/acme/payment-service",
            "path_with_namespace": "acme/payment-service",
        },
        "object_attributes": {
            "action": "open",
            "title": "Add review queue worker",
            "source_branch": "feature/review-queue",
            "target_branch": "main",
            "iid": 7,
            "last_commit": {"id": "abc123def456"},
        },
    }

    event = GitLabIntegrationAdapter().parse_webhook(
        payload,
        headers={"X-Gitlab-Event": "Merge Request Hook"},
    )

    assert event.external_event_id is None


def test_gitlab_adapter_rejects_unsupported_event() -> None:
    payload = {
        "object_kind": "tag_push",
        "event_name": "tag_push",
    }

    with pytest.raises(ValueError, match="Unsupported GitLab webhook event"):
        GitLabIntegrationAdapter().parse_webhook(
            payload,
            headers={"X-Gitlab-Event": "Tag Push Hook"},
        )
