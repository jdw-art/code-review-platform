from __future__ import annotations

from collections import defaultdict

import pytest

from app.agent.tool_gateway import AgentToolGateway


class FakeProvider:
    def __init__(self) -> None:
        self.calls = defaultdict(int)

    def list_files(self, *, path: str, ref: str) -> str:
        self.calls["list_files"] += 1
        return f"[F] {path}@{ref}"

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        self.calls["read_file"] += 1
        return f"# {path}@{ref}\n{start}:{end}\ntoken=sk-secret123456"

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        self.calls["search"] += 1
        return f"{path}@{ref}:{pattern}"

    def get_project_overview(self) -> str:
        self.calls["get_project_overview"] += 1
        return "overview"

    def get_recent_commits(self, *, limit: int) -> str:
        self.calls["get_recent_commits"] += 1
        return f"commits:{limit}"


def test_gateway_rejects_unknown_tool() -> None:
    gateway = AgentToolGateway(provider=FakeProvider())

    with pytest.raises(ValueError, match="unknown tool"):
        gateway.execute(
            "missing_tool",
            {},
            snapshot_id=1,
            history=[],
        )


def test_gateway_validates_read_file_line_range() -> None:
    gateway = AgentToolGateway(provider=FakeProvider())

    with pytest.raises(ValueError, match="invalid line range"):
        gateway.execute(
            "read_file",
            {"path": "README.md", "start": 10, "end": 1, "ref": "main"},
            snapshot_id=1,
            history=[],
        )


def test_gateway_blocks_third_identical_recent_tool_call() -> None:
    gateway = AgentToolGateway(provider=FakeProvider())
    history = [
        {"role": "tool", "name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20, "ref": "main"}},
        {"role": "tool", "name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20, "ref": "main"}},
    ]

    result = gateway.execute(
        "read_file",
        {"path": "README.md", "start": 1, "end": 20, "ref": "main"},
        snapshot_id=1,
        history=history,
    )

    assert result.status == "rejected"
    assert result.error_code == "repeated_identical_call"


def test_gateway_reuses_same_run_cache_for_same_snapshot() -> None:
    provider = FakeProvider()
    gateway = AgentToolGateway(provider=provider)

    first = gateway.execute(
        "read_file",
        {"path": "README.md", "start": 1, "end": 20, "ref": "main"},
        snapshot_id=5,
        history=[],
    )
    second = gateway.execute(
        "read_file",
        {"path": "README.md", "start": 1, "end": 20, "ref": "main"},
        snapshot_id=5,
        history=[],
    )

    assert first.cached is False
    assert second.cached is True
    assert provider.calls["read_file"] == 1


def test_gateway_redacts_secret_like_output_before_returning() -> None:
    gateway = AgentToolGateway(provider=FakeProvider())

    result = gateway.execute(
        "read_file",
        {"path": "README.md", "start": 1, "end": 20, "ref": "main"},
        snapshot_id=1,
        history=[],
    )

    assert "<redacted>" in result.output
    assert "sk-secret123456" not in result.output
