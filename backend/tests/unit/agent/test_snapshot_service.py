from __future__ import annotations

from app.db.models import Project, RepositorySnapshot


class FakeSnapshotProvider:
    def __init__(self, *, head_sha: str) -> None:
        self.head_sha = head_sha

    def get_head_sha(self, *, ref: str) -> str:
        assert ref == "main"
        return self.head_sha

    def get_file_tree(self, *, ref: str) -> list[dict[str, str]]:
        assert ref == "main"
        return [
            {"path": "README.md", "type": "file"},
            {"path": "backend/app/main.py", "type": "file"},
            {"path": "backend/app", "type": "dir"},
        ]

    def get_snapshot_overview(self, *, ref: str) -> dict[str, str]:
        assert ref == "main"
        return {"readme": "AI Code Reviewer"}

    def get_recent_commit_records(self, *, limit: int) -> list[dict[str, str]]:
        assert limit == 10
        return [{"id": "c1", "message": "feat: bootstrap"}]


def test_snapshot_service_creates_ready_snapshot_for_project(db_session) -> None:
    from app.agent.snapshot_service import RepositorySnapshotService

    project = Project(
        name="Repo Agent Demo",
        key="repo-agent-demo",
        platform_type="github",
        repo_url="https://example.com/demo.git",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    service = RepositorySnapshotService(db_session)

    snapshot = service.ensure_ready_snapshot(
        project=project,
        provider=FakeSnapshotProvider(head_sha="sha1"),
    )

    assert snapshot.project_id == project.id
    assert snapshot.status == "ready"
    assert snapshot.head_sha == "sha1"
    assert snapshot.overview["readme"] == "AI Code Reviewer"
    assert snapshot.recent_commits[0]["id"] == "c1"
    assert snapshot.indexed_paths == ["README.md", "backend/app/main.py"]

    stored = db_session.get(RepositorySnapshot, snapshot.id)
    assert stored is not None
    assert stored.fingerprint == snapshot.fingerprint


def test_snapshot_service_marks_existing_snapshot_stale_when_head_changes(db_session) -> None:
    from app.agent.snapshot_service import RepositorySnapshotService

    project = Project(
        name="Repo Agent Demo",
        key="repo-agent-stale",
        platform_type="gitlab",
        repo_url="https://example.com/stale.git",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    snapshot = RepositorySnapshot(
        project=project,
        platform_type=project.platform_type,
        repo_url=project.repo_url,
        ref="main",
        head_sha="old",
        fingerprint="fp-old",
        status="ready",
        file_tree=[],
        overview={},
        recent_commits=[],
        indexed_paths=[],
    )
    db_session.add_all([project, snapshot])
    db_session.commit()

    service = RepositorySnapshotService(db_session)
    service.mark_stale_snapshots(project_id=project.id, ref="main", new_head_sha="new")
    db_session.refresh(snapshot)

    assert snapshot.status == "stale"


def test_snapshot_fingerprint_changes_when_head_sha_changes(db_session) -> None:
    from app.agent.snapshot_service import RepositorySnapshotService

    service = RepositorySnapshotService(db_session)

    first = service.build_fingerprint(
        project_id=1,
        platform_type="github",
        repo_url="https://example.com/demo.git",
        ref="main",
        head_sha="sha1",
        tool_signature="tools-v1",
        settings_hash="settings-v1",
    )
    second = service.build_fingerprint(
        project_id=1,
        platform_type="github",
        repo_url="https://example.com/demo.git",
        ref="main",
        head_sha="sha2",
        tool_signature="tools-v1",
        settings_hash="settings-v1",
    )

    assert first != second
