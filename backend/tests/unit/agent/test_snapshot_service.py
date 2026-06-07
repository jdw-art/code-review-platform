from __future__ import annotations

from dataclasses import asdict
from urllib.error import HTTPError

from app.agent.repository_provider import FakeRepositoryProvider, RepositoryContentDecodeError
from app.agent.snapshot_service import SnapshotService
from app.agent.workspace import WorkspaceSnapshot, build_workspace_fingerprint
from app.db.models import Project


def test_snapshot_service_builds_workspace_snapshot_with_docs_tree_and_recent_commits() -> None:
    project = Project(
        id=11,
        name="repo-agent",
        key="repo-agent",
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        default_branch="main",
        settings={"external_repo_full_name": "acme/review-bot"},
    )
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={
            ("main", "README.md"): "# Repo Agent\nRead-only helper\n",
            ("main", "AGENTS.md"): "Keep answers grounded in the repository.\n",
            ("main", "backend/app/main.py"): "print('hello')\n",
        },
        recent_commits={
            "main": [
                "abc1234 feat: add repo agent",
                "def5678 docs: add agent instructions",
            ]
        },
    )

    snapshot = SnapshotService(provider=provider).build(project=project, branch="main")

    assert isinstance(snapshot, WorkspaceSnapshot)
    assert snapshot.project_id == "11"
    assert snapshot.platform_type == "github"
    assert snapshot.branch == "main"
    assert snapshot.head_sha == "sha-main"
    assert snapshot.default_branch == "main"
    assert snapshot.file_tree_summary == {
        "path": ".",
        "entries": ["AGENTS.md", "README.md", "backend/app/main.py"],
        "files": {
            "AGENTS.md": {
                "path": "AGENTS.md",
                "type": "blob",
                "file_version": snapshot.file_tree_summary["files"]["AGENTS.md"]["file_version"],
            },
            "README.md": {
                "path": "README.md",
                "type": "blob",
                "file_version": snapshot.file_tree_summary["files"]["README.md"]["file_version"],
            },
            "backend/app/main.py": {
                "path": "backend/app/main.py",
                "type": "blob",
                "file_version": snapshot.file_tree_summary["files"]["backend/app/main.py"]["file_version"],
            },
        },
    }
    assert snapshot.project_docs_summary == {
        "README.md": {
            "path": "README.md",
            "content": "1: # Repo Agent\n2: Read-only helper",
            "start": 1,
            "end": 2,
            "total_lines": 2,
            "file_version": snapshot.project_docs_summary["README.md"]["file_version"],
        },
        "AGENTS.md": {
            "path": "AGENTS.md",
            "content": "1: Keep answers grounded in the repository.",
            "start": 1,
            "end": 1,
            "total_lines": 1,
            "file_version": snapshot.project_docs_summary["AGENTS.md"]["file_version"],
        },
    }
    assert snapshot.recent_commits_summary == [
        "abc1234 feat: add repo agent",
        "def5678 docs: add agent instructions",
    ]
    assert len(snapshot.snapshot_digest) == 64
    assert build_workspace_fingerprint(snapshot)


def test_snapshot_service_digest_changes_when_snapshot_inputs_change() -> None:
    project = Project(
        id=12,
        name="repo-agent",
        key="repo-agent-2",
        platform_type="gitlab",
        repo_url="https://gitlab.example.com/acme/review-bot",
        default_branch="main",
        settings={"gitlab_project_path": "acme/review-bot", "external_project_id": "123"},
    )
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={("main", "README.md"): "# Repo Agent\nVersion 1\n"},
        recent_commits={"main": ["abc1234 feat: initial snapshot"]},
    )
    service = SnapshotService(provider=provider)

    first = service.build(project=project, branch="main")
    provider.files[("main", "README.md")] = "# Repo Agent\nVersion 2\n"
    second = service.build(project=project, branch="main")

    assert first.snapshot_digest != second.snapshot_digest


def test_snapshot_service_normalizes_project_id_and_workspace_fingerprint() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-main"},
        files={("main", "README.md"): "# Repo Agent\nVersion 1\n"},
        recent_commits={"main": ["abc1234 feat: initial snapshot"]},
    )
    service = SnapshotService(provider=provider)

    snapshot = service.build(
        branch="main",
        project_id=11,
        platform_type="github",
        default_branch="main",
    )

    assert snapshot.project_id == "11"

    payload = asdict(snapshot)
    payload["project_id"] = 11

    assert build_workspace_fingerprint(snapshot) == build_workspace_fingerprint(payload)


def test_snapshot_service_uses_resolved_head_sha_for_tree_and_doc_reads() -> None:
    class RecordingProvider(FakeRepositoryProvider):
        def __init__(self) -> None:
            super().__init__(
                branch_heads={"main": "sha-main"},
                files={
                    ("main", "README.md"): "# Repo Agent\nRead-only helper\n",
                    ("main", "backend/app/main.py"): "print('hello')\n",
                },
                recent_commits={"main": ["abc1234 feat: initial snapshot"]},
            )
            self.calls: list[tuple[str, str | None, str]] = []

        def list_tree(self, *, branch: str, path: str = ".", ref: str | None = None) -> dict[str, object]:
            self.calls.append(("list_tree", ref, path))
            return super().list_tree(branch=branch, path=path, ref=ref)

        def read_file(
            self,
            *,
            branch: str,
            path: str,
            start: int,
            end: int,
            ref: str | None = None,
        ) -> dict[str, object]:
            self.calls.append(("read_file", ref, path))
            return super().read_file(branch=branch, path=path, start=start, end=end, ref=ref)

        def get_recent_commits(
            self,
            *,
            branch: str,
            limit: int = 5,
            ref: str | None = None,
        ) -> list[str]:
            self.calls.append(("get_recent_commits", ref, branch))
            return super().get_recent_commits(branch=branch, limit=limit, ref=ref)

    provider = RecordingProvider()
    project = Project(
        id=13,
        name="repo-agent",
        key="repo-agent-3",
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        default_branch="main",
        settings={"external_repo_full_name": "acme/review-bot"},
    )

    SnapshotService(provider=provider).build(project=project, branch="main")

    assert ("list_tree", "sha-main", ".") in provider.calls
    assert ("read_file", "sha-main", "README.md") in provider.calls
    assert ("get_recent_commits", "sha-main", "main") in provider.calls


def test_snapshot_service_ignores_optional_doc_http_404() -> None:
    class MissingDocProvider(FakeRepositoryProvider):
        def read_file(
            self,
            *,
            branch: str,
            path: str,
            start: int,
            end: int,
            ref: str | None = None,
        ) -> dict[str, object]:
            if path == "AGENTS.md":
                raise HTTPError(url=path, code=404, msg="Not Found", hdrs=None, fp=None)
            return super().read_file(branch=branch, path=path, start=start, end=end, ref=ref)

    provider = MissingDocProvider(
        branch_heads={"main": "sha-main"},
        files={
            ("main", "README.md"): "# Repo Agent\nRead-only helper\n",
            ("main", "backend/app/main.py"): "print('hello')\n",
        },
        recent_commits={"main": ["abc1234 feat: initial snapshot"]},
    )
    project = Project(
        id=14,
        name="repo-agent",
        key="repo-agent-4",
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        default_branch="main",
        settings={"external_repo_full_name": "acme/review-bot"},
    )

    snapshot = SnapshotService(provider=provider).build(project=project, branch="main")

    assert "README.md" in snapshot.project_docs_summary
    assert "AGENTS.md" not in snapshot.project_docs_summary


def test_snapshot_service_ignores_optional_doc_decode_failure() -> None:
    class UndecodableDocProvider(FakeRepositoryProvider):
        def read_file(
            self,
            *,
            branch: str,
            path: str,
            start: int,
            end: int,
            ref: str | None = None,
        ) -> dict[str, object]:
            if path == "AGENTS.md":
                raise RepositoryContentDecodeError("not utf-8")
            return super().read_file(branch=branch, path=path, start=start, end=end, ref=ref)

    provider = UndecodableDocProvider(
        branch_heads={"main": "sha-main"},
        files={
            ("main", "README.md"): "# Repo Agent\nRead-only helper\n",
            ("main", "backend/app/main.py"): "print('hello')\n",
        },
        recent_commits={"main": ["abc1234 feat: initial snapshot"]},
    )
    project = Project(
        id=15,
        name="repo-agent",
        key="repo-agent-5",
        platform_type="github",
        repo_url="https://github.com/acme/review-bot",
        default_branch="main",
        settings={"external_repo_full_name": "acme/review-bot"},
    )

    snapshot = SnapshotService(provider=provider).build(project=project, branch="main")

    assert "README.md" in snapshot.project_docs_summary
    assert "AGENTS.md" not in snapshot.project_docs_summary
