from __future__ import annotations

import base64
import json
from urllib.error import HTTPError

import pytest

from app.agent.repository_provider import (
    FakeRepositoryProvider,
    GitHubRepositoryProvider,
    GitLabRepositoryProvider,
    RepositoryPaginationError,
)
from app.db.models import Project


def _make_project(
    *,
    project_id: int,
    platform_type: str,
    repo_url: str,
    default_branch: str = "main",
    settings: dict[str, object] | None = None,
) -> Project:
    return Project(
        id=project_id,
        name=f"{platform_type}-project",
        key=f"{platform_type}-{project_id}",
        platform_type=platform_type,
        repo_url=repo_url,
        default_branch=default_branch,
        settings=settings or {},
    )


def test_fake_repository_provider_exposes_read_only_repository_capabilities() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={
            ("main", "README.md"): "# Repo Agent\nRead-only project helper\n",
            ("main", "backend/app/main.py"): "from fastapi import FastAPI\napp = FastAPI()\n",
        },
        recent_commits={
            "main": [
                "abc1234 feat: add repo agent",
                "def5678 docs: add readme",
            ]
        },
        change_summaries={
            "18": {
                "external_id": "18",
                "title": "Add repo agent",
                "source_branch": "feature/repo-agent",
                "target_branch": "main",
            }
        },
        commit_lists={
            "18": [
                {
                    "id": "abc1234",
                    "message": "feat: add repo agent",
                }
            ]
        },
        comment_threads={
            "18": [
                {
                    "id": "thread-1",
                    "body": "Looks good overall.",
                }
            ]
        },
        diff_overviews={
            "18": {
                "external_id": "18",
                "files_changed": 2,
                "additions": 12,
                "deletions": 3,
            }
        },
    )

    assert provider.resolve_branch_head(branch="main") == "sha-main"

    tree = provider.list_tree(branch="main", path=".")
    assert tree["entries"] == ["README.md", "backend/app/main.py"]
    assert tree["files"]["README.md"]["type"] == "blob"

    file_payload = provider.read_file(branch="main", path="README.md", start=1, end=2)
    assert file_payload == {
        "path": "README.md",
        "content": "1: # Repo Agent\n2: Read-only project helper",
        "start": 1,
        "end": 2,
        "total_lines": 2,
        "file_version": file_payload["file_version"],
    }

    search_payload = provider.search_code(branch="main", query="fastapi", path="backend")
    assert search_payload == {
        "matches": [
            {
                "path": "backend/app/main.py",
                "line": 1,
                "text": "from fastapi import FastAPI",
            },
            {
                "path": "backend/app/main.py",
                "line": 2,
                "text": "app = FastAPI()",
            },
        ]
    }
    assert provider.get_recent_commits(branch="main", limit=1) == ["abc1234 feat: add repo agent"]
    assert provider.get_change_summary(external_id="18")["title"] == "Add repo agent"
    assert provider.list_commits(external_id="18")[0]["id"] == "abc1234"
    assert provider.list_comment_threads(external_id="18")[0]["id"] == "thread-1"
    assert provider.get_diff_overview(external_id="18")["files_changed"] == 2


def test_read_file_clamps_empty_windows_to_file_bounds() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={("main", "README.md"): "line 1\nline 2\n"},
    )

    assert provider.read_file(branch="main", path="README.md", start=100, end=120) == {
        "path": "README.md",
        "content": "",
        "start": 2,
        "end": 2,
        "total_lines": 2,
        "file_version": provider.read_file(
            branch="main",
            path="README.md",
            start=100,
            end=120,
        )["file_version"],
    }


def test_read_file_returns_consistent_empty_window_for_empty_file() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={("main", "README.md"): ""},
    )

    payload = provider.read_file(branch="main", path="README.md", start=1, end=20)

    assert payload == {
        "path": "README.md",
        "content": "",
        "start": 1,
        "end": 1,
        "total_lines": 0,
        "file_version": payload["file_version"],
    }


class _FakeResponse:
    def __init__(self, payload=None, *, raw_bytes: bytes | None = None) -> None:
        self.payload = payload
        self.raw_bytes = raw_bytes

    def read(self) -> bytes:
        if self.raw_bytes is not None:
            return self.raw_bytes
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


def test_github_repository_provider_builds_expected_urls_and_normalizes_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=1,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured_urls.append(request.full_url)
        if request.full_url.endswith("/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"sha": "sha-feature"}})
        if request.full_url.endswith("/git/trees/sha-feature?recursive=1"):
            return _FakeResponse(
                {
                    "tree": [
                        {"path": "README.md", "type": "blob", "sha": "blob-readme"},
                        {"path": "backend/app/main.py", "type": "blob", "sha": "blob-main"},
                    ]
                }
            )
        if request.full_url.endswith("/contents/backend%2Fapp%2Fmain.py?ref=feature%2Ftask-3"):
            return _FakeResponse(
                {
                    "sha": "blob-main",
                    "content": base64.b64encode(
                        b"from fastapi import FastAPI\napp = FastAPI()\n"
                    ).decode("utf-8"),
                    "encoding": "base64",
                }
            )
        if request.full_url.endswith("/commits?sha=feature%2Ftask-3&per_page=2"):
            return _FakeResponse(
                [
                    {
                        "sha": "abc123456789",
                        "commit": {"message": "feat: add repo agent\n\nbody"},
                    },
                    {
                        "sha": "def987654321",
                        "commit": {"message": "docs: add readme"},
                    },
                ]
            )
        if request.full_url.endswith("/pulls/18"):
            return _FakeResponse(
                {
                    "number": 18,
                    "title": "Add repo agent",
                    "state": "open",
                    "html_url": "https://github.com/acme/review-bot/pull/18",
                    "user": {"login": "alice"},
                    "head": {"ref": "feature/task-3", "sha": "sha-feature"},
                    "base": {"ref": "main", "sha": "sha-main"},
                }
            )
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    assert provider.resolve_branch_head(branch="feature/task-3") == "sha-feature"
    assert provider.list_tree(branch="feature/task-3", path=".") == {
        "path": ".",
        "entries": ["README.md", "backend/app/main.py"],
        "files": {
            "README.md": {
                "path": "README.md",
                "type": "blob",
                "file_version": "blob-readme",
            },
            "backend/app/main.py": {
                "path": "backend/app/main.py",
                "type": "blob",
                "file_version": "blob-main",
            },
        },
    }
    assert provider.read_file(
        branch="feature/task-3",
        path="backend/app/main.py",
        start=1,
        end=2,
    ) == {
        "path": "backend/app/main.py",
        "content": "1: from fastapi import FastAPI\n2: app = FastAPI()",
        "start": 1,
        "end": 2,
        "total_lines": 2,
        "file_version": "blob-main",
    }
    assert provider.get_recent_commits(branch="feature/task-3", limit=2) == [
        "abc1234 feat: add repo agent",
        "def9876 docs: add readme",
    ]
    assert provider.get_change_summary(external_id="18") == {
        "external_id": "18",
        "title": "Add repo agent",
        "state": "open",
        "url": "https://github.com/acme/review-bot/pull/18",
        "author": "alice",
        "source_branch": "feature/task-3",
        "target_branch": "main",
        "head_sha": "sha-feature",
        "base_sha": "sha-main",
    }

    assert any("/branches/feature%2Ftask-3" in url for url in captured_urls)
    assert any("/git/trees/sha-feature?recursive=1" in url for url in captured_urls)
    assert captured_urls[-1].endswith("/pulls/18")


def test_gitlab_repository_provider_builds_expected_urls_and_normalizes_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=2,
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/payment-service",
        settings={
            "gitlab_project_path": "acme/payment-service",
            "external_project_id": "123",
        },
    )
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured_urls.append(request.full_url)
        if request.full_url.endswith("/repository/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"id": "sha-feature"}})
        if request.full_url.endswith("/repository/tree?ref=feature%2Ftask-3&recursive=true&per_page=100&page=1"):
            return _FakeResponse(
                [
                    {"path": "README.md", "type": "blob", "id": "blob-readme"},
                    {"path": "backend/app/main.py", "type": "blob", "id": "blob-main"},
                ]
            )
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py/raw?ref=feature%2Ftask-3"
        ):
            return _FakeResponse(raw_bytes=b"from fastapi import FastAPI\napp = FastAPI()\n")
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py?ref=feature%2Ftask-3"
        ):
            return _FakeResponse({"blob_id": "blob-main"})
        if request.full_url.endswith("/repository/commits?ref_name=feature%2Ftask-3&per_page=2"):
            return _FakeResponse(
                [
                    {"id": "abc123456789", "title": "feat: add repo agent"},
                    {"id": "def987654321", "title": "docs: add readme"},
                ]
            )
        if request.full_url.endswith("/merge_requests/7"):
            return _FakeResponse(
                {
                    "iid": 7,
                    "title": "Add repo agent",
                    "state": "opened",
                    "web_url": "https://gitlab.example.com/acme/payment-service/-/merge_requests/7",
                    "author": {"username": "alice"},
                    "source_branch": "feature/task-3",
                    "target_branch": "main",
                    "diff_refs": {"head_sha": "sha-feature", "base_sha": "sha-main"},
                }
            )
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitLabRepositoryProvider(
        project=project,
        access_token="gl-token",
        base_url="https://gitlab.example.com",
    )

    assert provider.resolve_branch_head(branch="feature/task-3") == "sha-feature"
    assert provider.list_tree(branch="feature/task-3", path=".") == {
        "path": ".",
        "entries": ["README.md", "backend/app/main.py"],
        "files": {
            "README.md": {
                "path": "README.md",
                "type": "blob",
                "file_version": "blob-readme",
            },
            "backend/app/main.py": {
                "path": "backend/app/main.py",
                "type": "blob",
                "file_version": "blob-main",
            },
        },
    }
    assert provider.read_file(
        branch="feature/task-3",
        path="backend/app/main.py",
        start=1,
        end=2,
    ) == {
        "path": "backend/app/main.py",
        "content": "1: from fastapi import FastAPI\n2: app = FastAPI()",
        "start": 1,
        "end": 2,
        "total_lines": 2,
        "file_version": "blob-main",
    }
    assert provider.get_recent_commits(branch="feature/task-3", limit=2) == [
        "abc1234 feat: add repo agent",
        "def9876 docs: add readme",
    ]
    assert provider.get_change_summary(external_id="7") == {
        "external_id": "7",
        "title": "Add repo agent",
        "state": "opened",
        "url": "https://gitlab.example.com/acme/payment-service/-/merge_requests/7",
        "author": "alice",
        "source_branch": "feature/task-3",
        "target_branch": "main",
        "head_sha": "sha-feature",
        "base_sha": "sha-main",
    }

    assert any("/repository/branches/feature%2Ftask-3" in url for url in captured_urls)
    assert any(
        "/repository/tree?ref=feature%2Ftask-3&recursive=true&per_page=100&page=1" in url
        for url in captured_urls
    )
    assert captured_urls[-1].endswith("/merge_requests/7")


def test_github_repository_provider_search_code_reads_full_remote_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=3,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )
    late_match_content = "\n".join(
        [f"line {index}" for index in range(1, 401)] + ["needle match"] + ["line 402"]
    )

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"sha": "sha-feature"}})
        if request.full_url.endswith("/git/trees/sha-feature?recursive=1"):
            return _FakeResponse(
                {
                    "tree": [
                        {"path": "backend/app/main.py", "type": "blob", "sha": "blob-main"},
                    ]
                }
            )
        if request.full_url.endswith("/contents/backend%2Fapp%2Fmain.py?ref=sha-feature"):
            return _FakeResponse(
                {
                    "sha": "blob-main",
                    "content": base64.b64encode(late_match_content.encode("utf-8")).decode("utf-8"),
                    "encoding": "base64",
                }
            )
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    assert provider.search_code(branch="feature/task-3", query="needle", path="backend") == {
        "matches": [
            {
                "path": "backend/app/main.py",
                "line": 401,
                "text": "needle match",
            }
        ]
    }


def test_github_repository_provider_falls_back_when_recursive_tree_is_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=4,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"sha": "sha-feature"}})
        if request.full_url.endswith("/git/trees/sha-feature?recursive=1"):
            return _FakeResponse({"truncated": True, "tree": []})
        if request.full_url.endswith("/contents?ref=sha-feature"):
            return _FakeResponse(
                [
                    {"path": "README.md", "type": "file", "sha": "blob-readme"},
                    {"path": "backend", "type": "dir"},
                ]
            )
        if request.full_url.endswith("/contents/backend?ref=sha-feature"):
            return _FakeResponse(
                [
                    {"path": "backend/app.py", "type": "file", "sha": "blob-app"},
                ]
            )
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    assert provider.list_tree(branch="feature/task-3", path=".") == {
        "path": ".",
        "entries": ["README.md", "backend/app.py"],
        "files": {
            "README.md": {
                "path": "README.md",
                "type": "blob",
                "file_version": "blob-readme",
            },
            "backend/app.py": {
                "path": "backend/app.py",
                "type": "blob",
                "file_version": "blob-app",
            },
        },
    }


def test_github_repository_provider_paginates_commits_review_comments_and_diff_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=5,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )
    captured_urls: list[str] = []
    page_one_commits = [
        {
            "sha": f"sha-{index:03d}",
            "html_url": f"https://github.com/acme/review-bot/commit/sha-{index:03d}",
            "commit": {"message": f"commit {index}\n\nbody"},
        }
        for index in range(100)
    ]
    page_two_commits = [
        {
            "sha": "sha-100",
            "html_url": "https://github.com/acme/review-bot/commit/sha-100",
            "commit": {"message": "commit 100"},
        }
    ]
    page_one_comments = [
        {
            "id": index + 1,
            "body": f"comment {index + 1}",
            "created_at": f"2026-06-04T00:{index % 60:02d}:00Z",
            "path": "backend/app/main.py",
            "line": index + 1,
            "start_line": None,
            "side": "RIGHT",
            "user": {"login": "alice"},
        }
        for index in range(100)
    ]
    page_two_comments = [
        {
            "id": 101,
            "body": "follow up",
            "created_at": "2026-06-04T01:00:00Z",
            "path": "backend/app/main.py",
            "line": 101,
            "start_line": None,
            "side": "RIGHT",
            "user": {"login": "bob"},
            "in_reply_to_id": 100,
        }
    ]
    page_one_files = [
        {
            "filename": f"backend/file_{index}.py",
            "status": "modified",
            "additions": 2,
            "deletions": 1,
        }
        for index in range(100)
    ]
    page_two_files = [
        {
            "filename": "backend/file_100.py",
            "status": "added",
            "additions": 4,
            "deletions": 0,
        }
    ]

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured_urls.append(request.full_url)
        if request.full_url.endswith("/pulls/18/commits?per_page=100&page=1"):
            return _FakeResponse(page_one_commits)
        if request.full_url.endswith("/pulls/18/commits?per_page=100&page=2"):
            return _FakeResponse(page_two_commits)
        if request.full_url.endswith("/pulls/18/comments?per_page=100&page=1"):
            return _FakeResponse(page_one_comments)
        if request.full_url.endswith("/pulls/18/comments?per_page=100&page=2"):
            return _FakeResponse(page_two_comments)
        if request.full_url.endswith("/pulls/18/files?per_page=100&page=1"):
            return _FakeResponse(page_one_files)
        if request.full_url.endswith("/pulls/18/files?per_page=100&page=2"):
            return _FakeResponse(page_two_files)
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    commits = provider.list_commits(external_id="18")
    assert len(commits) == 101
    assert commits[0] == {
        "id": "sha-000",
        "message": "commit 0\n\nbody",
        "title": "commit 0",
        "url": "https://github.com/acme/review-bot/commit/sha-000",
    }
    assert commits[-1]["id"] == "sha-100"

    threads = provider.list_comment_threads(external_id="18")
    assert len(threads) == 100
    assert threads[0] == {
        "id": 1,
        "body": "comment 1",
        "author": "alice",
        "created_at": "2026-06-04T00:00:00Z",
        "path": "backend/app/main.py",
        "line": 1,
        "start_line": None,
        "resolved": None,
        "notes": [
            {
                "id": 1,
                "body": "comment 1",
                "author": "alice",
                "created_at": "2026-06-04T00:00:00Z",
                "path": "backend/app/main.py",
                "line": 1,
                "start_line": None,
                "side": "RIGHT",
                "resolved": None,
            }
        ],
    }
    assert threads[-1]["id"] == 100
    assert threads[-1]["notes"][-1]["id"] == 101
    assert threads[-1]["notes"][-1]["author"] == "bob"

    diff_overview = provider.get_diff_overview(external_id="18")
    assert diff_overview == {
        "external_id": "18",
        "files_changed": 101,
        "additions": 204,
        "deletions": 100,
        "files": [
            {
                "path": "backend/file_0.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_1.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_2.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_3.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_4.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_5.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_6.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_7.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_8.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            {
                "path": "backend/file_9.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            },
            *[
                {
                    "path": f"backend/file_{index}.py",
                    "status": "modified",
                    "additions": 2,
                    "deletions": 1,
                }
                for index in range(10, 100)
            ],
            {
                "path": "backend/file_100.py",
                "status": "added",
                "additions": 4,
                "deletions": 0,
            },
        ],
    }

    assert any(url.endswith("/pulls/18/commits?per_page=100&page=2") for url in captured_urls)
    assert any(url.endswith("/pulls/18/comments?per_page=100&page=2") for url in captured_urls)
    assert any(url.endswith("/pulls/18/files?per_page=100&page=2") for url in captured_urls)


def test_gitlab_repository_provider_search_code_reads_full_remote_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=6,
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/payment-service",
        settings={
            "gitlab_project_path": "acme/payment-service",
            "external_project_id": "123",
        },
    )
    late_match_content = "\n".join(
        [f"line {index}" for index in range(1, 401)] + ["needle match"] + ["line 402"]
    )

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/repository/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"id": "sha-feature"}})
        if request.full_url.endswith(
            "/repository/tree?ref=sha-feature&recursive=true&per_page=100&page=1"
        ):
            return _FakeResponse(
                [
                    {"path": "backend/app/main.py", "type": "blob", "id": "blob-main"},
                ]
            )
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py?ref=sha-feature"
        ):
            return _FakeResponse({"blob_id": "blob-main"})
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py/raw?ref=sha-feature"
        ):
            return _FakeResponse(raw_bytes=late_match_content.encode("utf-8"))
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitLabRepositoryProvider(
        project=project,
        access_token="gl-token",
        base_url="https://gitlab.example.com",
    )

    assert provider.search_code(branch="feature/task-3", query="needle", path="backend") == {
        "matches": [
            {
                "path": "backend/app/main.py",
                "line": 401,
                "text": "needle match",
            }
        ]
    }


def test_gitlab_repository_provider_paginates_tree_commits_and_discussions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=7,
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/payment-service",
        settings={
            "gitlab_project_path": "acme/payment-service",
            "external_project_id": "123",
        },
    )
    captured_urls: list[str] = []
    page_one_tree = [
        {"path": f"src/file_{index}.py", "type": "blob", "id": f"blob-{index}"}
        for index in range(100)
    ]
    page_two_tree = [{"path": "src/file_100.py", "type": "blob", "id": "blob-100"}]
    page_one_commits = [
        {
            "id": f"sha-{index:03d}",
            "title": f"commit {index}",
            "message": f"commit {index}\n\nbody",
            "web_url": f"https://gitlab.example.com/acme/payment-service/-/commit/sha-{index:03d}",
        }
        for index in range(100)
    ]
    page_two_commits = [
        {
            "id": "sha-100",
            "title": "commit 100",
            "message": "commit 100",
            "web_url": "https://gitlab.example.com/acme/payment-service/-/commit/sha-100",
        }
    ]
    page_one_discussions = [
        {
            "id": f"discussion-{index}",
            "resolved": False,
            "notes": [
                {
                    "id": index,
                    "body": f"note {index}",
                    "created_at": f"2026-06-04T00:{index % 60:02d}:00Z",
                    "author": {"username": "alice"},
                    "position": {
                        "new_path": "backend/app/main.py",
                        "new_line": index + 1,
                    },
                }
            ],
        }
        for index in range(100)
    ]
    page_two_discussions = [
        {
            "id": "discussion-100",
            "resolved": True,
            "notes": [
                {
                    "id": 100,
                    "body": "resolved note",
                    "created_at": "2026-06-04T01:00:00Z",
                    "author": {"username": "bob"},
                    "position": {
                        "new_path": "backend/app/main.py",
                        "new_line": 101,
                    },
                    "resolved": True,
                }
            ],
        }
    ]
    changes_payload = {
        "changes": [
            {
                "new_path": "backend/app/main.py",
                "old_path": "backend/app/main.py",
                "diff": "@@ -1 +1,2 @@\n-line 1\n+line 1\n+line 2\n",
                "new_file": False,
                "deleted_file": False,
            }
        ]
    }

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        captured_urls.append(request.full_url)
        if request.full_url.endswith(
            "/repository/tree?ref=feature%2Ftask-3&recursive=true&per_page=100&page=1"
        ):
            return _FakeResponse(page_one_tree)
        if request.full_url.endswith(
            "/repository/tree?ref=feature%2Ftask-3&recursive=true&per_page=100&page=2"
        ):
            return _FakeResponse(page_two_tree)
        if request.full_url.endswith("/merge_requests/7/commits?per_page=100&page=1"):
            return _FakeResponse(page_one_commits)
        if request.full_url.endswith("/merge_requests/7/commits?per_page=100&page=2"):
            return _FakeResponse(page_two_commits)
        if request.full_url.endswith("/merge_requests/7/discussions?per_page=100&page=1"):
            return _FakeResponse(page_one_discussions)
        if request.full_url.endswith("/merge_requests/7/discussions?per_page=100&page=2"):
            return _FakeResponse(page_two_discussions)
        if request.full_url.endswith("/merge_requests/7/changes"):
            return _FakeResponse(changes_payload)
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitLabRepositoryProvider(
        project=project,
        access_token="gl-token",
        base_url="https://gitlab.example.com",
    )

    tree = provider.list_tree(branch="feature/task-3", path="src")
    assert tree["entries"][0] == "src/file_0.py"
    assert len(tree["entries"]) == 101
    assert "src/file_100.py" in tree["entries"]

    commits = provider.list_commits(external_id="7")
    assert len(commits) == 101
    assert commits[0] == {
        "id": "sha-000",
        "message": "commit 0\n\nbody",
        "title": "commit 0",
        "url": "https://gitlab.example.com/acme/payment-service/-/commit/sha-000",
    }
    assert commits[-1]["id"] == "sha-100"

    discussions = provider.list_comment_threads(external_id="7")
    assert len(discussions) == 101
    assert discussions[0] == {
        "id": "discussion-0",
        "body": "note 0",
        "author": "alice",
        "created_at": "2026-06-04T00:00:00Z",
        "path": "backend/app/main.py",
        "line": 1,
        "resolved": False,
        "notes": [
            {
                "id": 0,
                "body": "note 0",
                "author": "alice",
                "created_at": "2026-06-04T00:00:00Z",
                "path": "backend/app/main.py",
                "line": 1,
                "resolved": None,
            }
        ],
    }
    assert discussions[-1]["resolved"] is True
    assert discussions[-1]["notes"][0]["author"] == "bob"

    assert provider.get_diff_overview(external_id="7") == {
        "external_id": "7",
        "files_changed": 1,
        "additions": 2,
        "deletions": 1,
        "files": [
            {
                "path": "backend/app/main.py",
                "status": "modified",
                "additions": 2,
                "deletions": 1,
            }
        ],
    }

    assert any(
        url.endswith("/repository/tree?ref=feature%2Ftask-3&recursive=true&per_page=100&page=2")
        for url in captured_urls
    )


def test_github_repository_provider_search_code_skips_non_utf8_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=8,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/branches/feature%2Ftask-3"):
            return _FakeResponse({"commit": {"sha": "sha-feature"}})
        if request.full_url.endswith("/git/trees/sha-feature?recursive=1"):
            return _FakeResponse(
                {
                    "tree": [
                        {"path": "backend/app/binary.bin", "type": "blob", "sha": "blob-binary"},
                        {"path": "backend/app/main.py", "type": "blob", "sha": "blob-main"},
                    ]
                }
            )
        if request.full_url.endswith("/contents/backend%2Fapp%2Fbinary.bin?ref=sha-feature"):
            return _FakeResponse(
                {
                    "sha": "blob-binary",
                    "content": base64.b64encode(b"\xff\xfe\x00").decode("utf-8"),
                    "encoding": "base64",
                }
            )
        if request.full_url.endswith("/contents/backend%2Fapp%2Fmain.py?ref=sha-feature"):
            return _FakeResponse(
                {
                    "sha": "blob-main",
                    "content": base64.b64encode(b"line 1\nneedle match\n").decode("utf-8"),
                    "encoding": "base64",
                }
            )
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    assert provider.search_code(branch="feature/task-3", query="needle", path="backend") == {
        "matches": [
            {
                "path": "backend/app/main.py",
                "line": 2,
                "text": "needle match",
            }
        ]
    }


def test_gitlab_repository_provider_preserves_raw_text_content_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=9,
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/payment-service",
        settings={
            "gitlab_project_path": "acme/payment-service",
            "external_project_id": "123",
        },
    )
    raw_content = b"\"hello\\nworld\""

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/repository/files/backend%2Fapp%2Fmain.py?ref=feature%2Ftask-3"):
            return _FakeResponse({"blob_id": "blob-main"})
        if request.full_url.endswith("/repository/files/backend%2Fapp%2Fmain.py/raw?ref=feature%2Ftask-3"):
            return _FakeResponse(raw_bytes=raw_content)
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitLabRepositoryProvider(
        project=project,
        access_token="gl-token",
        base_url="https://gitlab.example.com",
    )

    assert provider.read_file(
        branch="feature/task-3",
        path="backend/app/main.py",
        start=1,
        end=1,
    ) == {
        "path": "backend/app/main.py",
        "content": '1: "hello\\nworld"',
        "start": 1,
        "end": 1,
        "total_lines": 1,
        "file_version": "blob-main",
    }


def test_gitlab_repository_provider_search_code_skips_non_utf8_raw_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=10,
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/payment-service",
        settings={
            "gitlab_project_path": "acme/payment-service",
            "external_project_id": "123",
        },
    )

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith(
            "/repository/tree?ref=sha-feature&recursive=true&per_page=100&page=1"
        ):
            return _FakeResponse(
                [
                    {"path": "backend/app/binary.bin", "type": "blob", "id": "blob-binary"},
                    {"path": "backend/app/main.py", "type": "blob", "id": "blob-main"},
                ]
            )
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fbinary.bin?ref=sha-feature"
        ):
            return _FakeResponse({"blob_id": "blob-binary"})
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fbinary.bin/raw?ref=sha-feature"
        ):
            return _FakeResponse(raw_bytes=b"\xff\xfe\x00")
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py?ref=sha-feature"
        ):
            return _FakeResponse({"blob_id": "blob-main"})
        if request.full_url.endswith(
            "/repository/files/backend%2Fapp%2Fmain.py/raw?ref=sha-feature"
        ):
            return _FakeResponse(raw_bytes=b"line 1\nneedle match\n")
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitLabRepositoryProvider(
        project=project,
        access_token="gl-token",
        base_url="https://gitlab.example.com",
    )

    assert provider.search_code(
        branch="feature/task-3",
        query="needle",
        path="backend",
        ref="sha-feature",
    ) == {
        "matches": [
            {
                "path": "backend/app/main.py",
                "line": 2,
                "text": "needle match",
            }
        ]
    }


def test_paginated_repository_provider_raises_on_unexpected_second_page_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _make_project(
        project_id=11,
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        settings={"external_repo_full_name": "acme/review-bot"},
    )
    page_one_commits = [
        {
            "sha": f"sha-{index:03d}",
            "html_url": f"https://github.com/acme/review-bot/commit/sha-{index:03d}",
            "commit": {"message": f"commit {index}"},
        }
        for index in range(100)
    ]

    def fake_urlopen(request, timeout: int = 10):
        del timeout
        if request.full_url.endswith("/pulls/18/commits?per_page=100&page=1"):
            return _FakeResponse(page_one_commits)
        if request.full_url.endswith("/pulls/18/commits?per_page=100&page=2"):
            return _FakeResponse({"message": "unexpected"})
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr("app.agent.repository_provider.urlopen", fake_urlopen)

    provider = GitHubRepositoryProvider(project=project, access_token="gh-token")

    with pytest.raises(RepositoryPaginationError):
        provider.list_commits(external_id="18")
