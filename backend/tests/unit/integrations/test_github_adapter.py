from __future__ import annotations

import pytest

from app.integrations.github import GitHubIntegrationAdapter


def test_github_adapter_normalizes_pull_request_event() -> None:
    payload = {
        "action": "opened",
        "sender": {"login": "octocat"},
        "repository": {
            "full_name": "acme/review-bot",
            "html_url": "https://github.com/acme/review-bot",
            "id": 99,
        },
        "pull_request": {
            "number": 18,
            "title": "Add GitHub adapter",
            "user": {"login": "pr-author"},
            "head": {
                "ref": "feature/github-adapter",
                "sha": "123abc456def",
            },
            "base": {"ref": "main"},
        },
    }

    event = GitHubIntegrationAdapter().parse_webhook(
        payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-pr-001",
        },
    )

    assert event.platform_type == "github"
    assert event.event_type == "pull_request"
    assert event.action == "opened"
    assert event.author == "pr-author"
    assert event.title == "Add GitHub adapter"
    assert event.branch is None
    assert event.source_branch == "feature/github-adapter"
    assert event.target_branch == "main"
    assert event.repo_url == "https://github.com/acme/review-bot"
    assert event.repo_full_name == "acme/review-bot"
    assert event.external_project_id == "99"
    assert event.external_event_id == "delivery-pr-001"
    assert event.last_commit_id == "123abc456def"
    assert event.webhook_data == payload


def test_github_adapter_accepts_lowercase_header_keys() -> None:
    payload = {
        "ref": "refs/heads/main",
        "after": "789fed654cba",
        "sender": {"login": "hubot"},
        "repository": {
            "full_name": "acme/api",
            "html_url": "https://github.com/acme/api",
            "id": 101,
        },
        "head_commit": {
            "id": "789fed654cba",
            "message": "Ship webhook parser",
        },
    }

    event = GitHubIntegrationAdapter().parse_webhook(
        payload,
        headers={
            "x-github-event": "push",
            "x-github-delivery": "delivery-push-lowercase",
        },
    )

    assert event.event_type == "push"
    assert event.external_event_id == "delivery-push-lowercase"


def test_github_adapter_normalizes_push_event() -> None:
    payload = {
        "ref": "refs/heads/main",
        "after": "789fed654cba",
        "sender": {"login": "hubot"},
        "repository": {
            "full_name": "acme/api",
            "html_url": "https://github.com/acme/api",
            "id": 101,
        },
        "head_commit": {
            "id": "789fed654cba",
            "message": "Ship webhook parser",
        },
    }

    event = GitHubIntegrationAdapter().parse_webhook(
        payload,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-push-001",
        },
    )

    assert event.platform_type == "github"
    assert event.event_type == "push"
    assert event.action == "push"
    assert event.author == "hubot"
    assert event.title == "Ship webhook parser"
    assert event.branch == "main"
    assert event.source_branch is None
    assert event.target_branch is None
    assert event.repo_url == "https://github.com/acme/api"
    assert event.repo_full_name == "acme/api"
    assert event.external_project_id == "101"
    assert event.external_event_id == "delivery-push-001"
    assert event.last_commit_id == "789fed654cba"
    assert event.webhook_data == payload


def test_github_adapter_raises_clear_error_when_event_header_missing() -> None:
    with pytest.raises(ValueError, match="Missing GitHub webhook event header"):
        GitHubIntegrationAdapter().parse_webhook(
            {"action": "opened"},
            headers={"X-GitHub-Delivery": "delivery-missing-event"},
        )


def test_github_adapter_rejects_unsupported_event() -> None:
    with pytest.raises(ValueError, match="Unsupported GitHub webhook event"):
        GitHubIntegrationAdapter().parse_webhook(
            {"action": "opened"},
            headers={
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "delivery-issues-001",
            },
        )
