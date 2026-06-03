from __future__ import annotations

from typing import Protocol


class RepositoryContentProvider(Protocol):
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
