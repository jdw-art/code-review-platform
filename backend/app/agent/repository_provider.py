from __future__ import annotations

from typing import Any, Protocol


class RepositoryContentProvider(Protocol):
    def get_head_sha(self, *, ref: str) -> str:
        pass

    def get_file_tree(self, *, ref: str) -> list[dict[str, Any]]:
        pass

    def get_snapshot_overview(self, *, ref: str) -> dict[str, Any]:
        pass

    def get_recent_commit_records(self, *, limit: int) -> list[dict[str, Any]]:
        pass

    def list_files(self, *, path: str, ref: str) -> str:
        pass

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        pass

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        pass

    def get_project_overview(self) -> str:
        pass

    def get_recent_commits(self, *, limit: int) -> str:
        pass
