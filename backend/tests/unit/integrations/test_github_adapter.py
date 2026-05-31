from __future__ import annotations

import json

import pytest

from app.db.models import ReviewRecord
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


class _FakeResponse:
    def __init__(self, payload) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


def test_github_adapter_fetches_pull_request_files(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        return _FakeResponse(
            [
                {
                    "filename": "worker.py",
                    "patch": "+pass",
                    "status": "modified",
                    "additions": 1,
                    "deletions": 0,
                }
            ]
        )

    monkeypatch.setattr("app.integrations.github.urlopen", fake_urlopen)
    adapter = GitHubIntegrationAdapter(access_token="gh-token")
    record = ReviewRecord(
        event_type="pull_request",
        platform_type="github",
        external_pull_request_id="18",
        webhook_data={"repository": {"full_name": "acme/review-bot"}},
        url="https://github.com/acme/review-bot/pull/18",
    )

    files = adapter.fetch_changes(record)

    assert files == [
        {
            "old_path": "worker.py",
            "new_path": "worker.py",
            "diff": "+pass",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
        }
    ]
    assert captured["auth"] == "token gh-token"
    assert captured["url"] == "https://api.github.com/repos/acme/review-bot/pulls/18/files"


def test_github_adapter_fetches_pull_request_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int = 10):
        del request, timeout
        return _FakeResponse(
            [
                {
                    "sha": "abc123",
                    "html_url": "https://github.com/acme/review-bot/commit/abc123",
                    "commit": {
                        "message": "feat: add worker\n\nbody",
                        "author": {
                            "name": "alice",
                            "email": "alice@example.com",
                            "date": "2026-05-31T08:00:00Z",
                        },
                    },
                }
            ]
        )

    monkeypatch.setattr("app.integrations.github.urlopen", fake_urlopen)
    adapter = GitHubIntegrationAdapter(access_token="gh-token")
    record = ReviewRecord(
        event_type="pull_request",
        platform_type="github",
        external_pull_request_id="18",
        webhook_data={"repository": {"full_name": "acme/review-bot"}},
        url="https://github.com/acme/review-bot/pull/18",
    )

    commits = adapter.fetch_commits(record)

    assert commits == [
        {
            "id": "abc123",
            "title": "feat: add worker",
            "message": "feat: add worker\n\nbody",
            "author_name": "alice",
            "author_email": "alice@example.com",
            "created_at": "2026-05-31T08:00:00Z",
            "web_url": "https://github.com/acme/review-bot/commit/abc123",
        }
    ]


def test_github_adapter_fetches_push_changes_from_commit_api_for_initial_branch_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured_urls.append(request.full_url)
        return _FakeResponse(
            {
                "files": [
                    {
                        "filename": "README.md",
                        "patch": "+hello",
                        "status": "modified",
                        "additions": 1,
                        "deletions": 0,
                    }
                ]
            }
        )

    monkeypatch.setattr("app.integrations.github.urlopen", fake_urlopen)
    adapter = GitHubIntegrationAdapter(access_token="gh-token")
    record = ReviewRecord(
        event_type="push",
        platform_type="github",
        last_commit_id="86617ef4dd4d15088d455731a9cc9b5954ccaa91",
        webhook_data={
            "before": "0000000000000000000000000000000000000000",
            "after": "86617ef4dd4d15088d455731a9cc9b5954ccaa91",
            "commits": [{"id": "86617ef4dd4d15088d455731a9cc9b5954ccaa91"}],
            "repository": {"full_name": "acme/review-bot"},
        },
        url="https://github.com/acme/review-bot",
    )

    files = adapter.fetch_changes(record)

    assert files == [
        {
            "old_path": "README.md",
            "new_path": "README.md",
            "diff": "+hello",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
        }
    ]
    assert captured_urls == [
        "https://api.github.com/repos/acme/review-bot/commits/86617ef4dd4d15088d455731a9cc9b5954ccaa91"
    ]


def test_github_adapter_posts_pull_request_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse({"id": 1})

    monkeypatch.setattr("app.integrations.github.urlopen", fake_urlopen)
    adapter = GitHubIntegrationAdapter(access_token="gh-token")
    record = ReviewRecord(
        event_type="pull_request",
        platform_type="github",
        external_pull_request_id="18",
        webhook_data={"repository": {"full_name": "acme/review-bot"}},
        url="https://github.com/acme/review-bot/pull/18",
    )

    adapter.publish_review_comment(record=record, review_result="Auto Review Result")

    assert captured["method"] == "POST"
    assert captured["body"] == {"body": "Auto Review Result"}
    assert captured["url"] == "https://api.github.com/repos/acme/review-bot/issues/18/comments"
