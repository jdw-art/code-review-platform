from __future__ import annotations

import json

from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.tool_gateway import ToolGateway


def test_tool_gateway_rejects_repeated_identical_call() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=["secret-token"],
    )

    first = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})
    second = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})

    assert "# Title" in first
    assert second.startswith("error: repeated identical tool call")


def test_tool_gateway_redacts_sensitive_text() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "token=secret-token\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=["secret-token"],
    )

    result = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})

    assert "secret-token" not in result
    assert "<redacted>" in result


def test_tool_gateway_redacts_secret_assignment_values_and_common_token_shapes() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            (
                "main",
                "README.md",
            ): "password=hunter2\ngithub=ghp_1234567890abcdefghijklmnopqrstuv\njwt=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.signature\n",
        },
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 20})

    assert "hunter2" not in result
    assert "ghp_1234567890abcdefghijklmnopqrstuv" not in result
    assert "eyJhbGciOiJIUzI1NiJ9" not in result
    assert result.count("<redacted>") >= 3


def test_tool_gateway_redacts_json_shaped_secret_text() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "README.md"): '{"password":"hunter2","token":"abc123","nested":{"secret":"top-secret"}}\n',
        },
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 20})

    assert "hunter2" not in result
    assert "abc123" not in result
    assert "top-secret" not in result
    assert result.count("<redacted>") >= 3


def test_tool_gateway_exposes_read_project_doc_from_snapshot_docs() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "README.md"): "# Repo Agent\nRead me first\n",
            ("main", "AGENTS.md"): "Follow repository rules\n",
        },
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
        project_docs_summary={
            "README.md": provider.read_file(branch="main", path="README.md", start=1, end=20),
            "AGENTS.md": provider.read_file(branch="main", path="AGENTS.md", start=1, end=20),
        },
    )

    result = gateway.run("read_project_doc", {"name": "AGENTS.md"})

    assert "Follow repository rules" in result


def test_tool_gateway_rejects_unknown_project_doc_name() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Repo Agent\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
        project_docs_summary={
            "README.md": provider.read_file(branch="main", path="README.md", start=1, end=20),
        },
    )

    result = gateway.run("read_project_doc", {"name": "missing.md"})

    assert result == "error: invalid arguments for read_project_doc: unknown project doc 'missing.md'"


def test_tool_gateway_validates_required_arguments() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("read_file", {"path": "", "start": 1, "end": 10})

    assert result == "error: invalid arguments for read_file: path must not be empty"


def test_tool_gateway_rejects_path_traversal_and_absolute_paths() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    traversal = gateway.run("read_file", {"path": "../secrets.env", "start": 1, "end": 10})
    absolute = gateway.run("list_files", {"path": "/etc"})

    assert traversal == "error: invalid arguments for read_file: path must stay within repository scope"
    assert absolute == "error: invalid arguments for list_files: path must stay within repository scope"


def test_tool_gateway_rejects_invalid_external_id_shape() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("get_change_summary", {"external_id": "bad id\n"})

    assert result == "error: invalid arguments for get_change_summary: external_id has invalid format"


def test_tool_gateway_rejects_read_file_windows_above_line_limit() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 500})

    assert result == "error: invalid arguments for read_file: line window exceeds maximum of 200 lines"


def test_tool_gateway_rejects_empty_locked_ref_when_provided() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )

    try:
        ToolGateway(
            provider=provider,
            branch="main",
            ref="   ",
            secret_values=[],
        )
    except ValueError as exc:
        assert str(exc) == "locked ref must not be empty when provided"
    else:
        raise AssertionError("expected ValueError for empty locked ref")


def test_tool_gateway_rejects_unknown_tool() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("run_shell", {"command": "pwd"})

    assert result == "error: unknown tool 'run_shell'"


def test_tool_gateway_rejects_non_consecutive_semantically_identical_search() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "README.md"): "# Title\n",
            ("main", "backend/app.py"): "needle value\n",
        },
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    first = gateway.run("search_code", {"query": "needle", "path": "backend"})
    middle = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})
    repeated = gateway.run("search_code", {"query": "Needle", "path": "backend"})

    assert "backend/app.py:1:needle value" in first
    assert "# Title" in middle
    assert repeated.startswith("error: repeated identical tool call")


def test_tool_gateway_clips_large_search_results() -> None:
    files = {
        ("main", f"backend/file_{index}.py"): "needle value\n"
        for index in range(150)
    }
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files=files,
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("search_code", {"query": "needle", "path": "backend"})
    lines = [line for line in result.splitlines() if line.strip()]

    assert len(lines) == 100
    assert lines[0].startswith("backend/file_0.py:1:")


def test_tool_gateway_clips_large_list_files_results() -> None:
    files = {
        ("main", f"backend/file_{index}.py"): "print('x')\n"
        for index in range(250)
    }
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files=files,
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("list_files", {"path": "backend"})
    lines = [line for line in result.splitlines() if line.strip()]

    assert len(lines) == 200


def test_tool_gateway_reports_invalid_provider_payload_for_list_files() -> None:
    class InvalidListProvider(FakeRepositoryProvider):
        def list_tree(self, *, branch: str, path: str = ".", ref: str | None = None) -> dict[str, object]:
            del branch, path, ref
            return {"entries": "bad-payload"}

    gateway = ToolGateway(
        provider=InvalidListProvider(branch_heads={"main": "sha-1"}, files={}),
        branch="main",
        secret_values=[],
    )

    result = gateway.run("list_files", {"path": "."})

    assert result == "error: invalid provider result for list_files"


def test_tool_gateway_reports_invalid_provider_payload_for_search_code() -> None:
    class InvalidSearchProvider(FakeRepositoryProvider):
        def search_code(
            self,
            *,
            branch: str,
            query: str,
            path: str = ".",
            ref: str | None = None,
        ) -> dict[str, object]:
            del branch, query, path, ref
            return {"matches": "bad-payload"}

    gateway = ToolGateway(
        provider=InvalidSearchProvider(branch_heads={"main": "sha-1"}, files={}),
        branch="main",
        secret_values=[],
    )

    result = gateway.run("search_code", {"query": "needle", "path": "."})

    assert result == "error: invalid provider result for search_code"


def test_tool_gateway_returns_valid_truncated_json_for_large_payload() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
        commit_lists={
            "18": [
                {
                    "id": str(index),
                    "message": "x" * 2000,
                    "title": f"commit {index}",
                    "url": f"https://example.com/{index}",
                }
                for index in range(20)
            ]
        },
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    result = gateway.run("list_commits", {"external_id": "18"})
    payload = json.loads(result)

    assert payload["truncated"] is True
    assert payload["kind"] == "list"
    assert payload["item_count"] == 20


def test_tool_gateway_returns_json_tool_signature_for_read_only_tools() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Title\n"},
    )
    gateway = ToolGateway(
        provider=provider,
        branch="main",
        secret_values=[],
    )

    payload = json.loads(gateway.tool_signature())

    assert [item["name"] for item in payload] == [
        "get_change_summary",
        "get_diff_overview",
        "list_comment_threads",
        "list_commits",
        "list_files",
        "read_file",
        "read_project_doc",
        "search_code",
    ]
    assert all(item["risky"] is False for item in payload)
    by_name = {item["name"]: item for item in payload}
    assert "up to 200 paths" in by_name["list_files"]["description"]
    assert "numbered lines only" in by_name["read_file"]["description"]
    assert "case-insensitive" in by_name["search_code"]["description"]
    assert by_name["read_project_doc"]["available_names"] == []
