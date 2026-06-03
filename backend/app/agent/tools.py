from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risky: bool
    description: str
    schema: dict[str, str]


READ_ONLY_TOOL_SPECS: dict[str, ToolSpec] = {
    "list_files": ToolSpec(
        name="list_files",
        risky=False,
        description="List files in the repository snapshot.",
        schema={"path": "str='.'", "ref": "str='main'"},
    ),
    "read_file": ToolSpec(
        name="read_file",
        risky=False,
        description="Read a file by line range.",
        schema={"path": "str", "start": "int=1", "end": "int=200", "ref": "str='main'"},
    ),
    "search": ToolSpec(
        name="search",
        risky=False,
        description="Search repository content.",
        schema={"pattern": "str", "path": "str='.'", "ref": "str='main'"},
    ),
    "get_project_overview": ToolSpec(
        name="get_project_overview",
        risky=False,
        description="Get repository overview.",
        schema={},
    ),
    "get_recent_commits": ToolSpec(
        name="get_recent_commits",
        risky=False,
        description="Get recent commits.",
        schema={"limit": "int=10"},
    ),
}


def validate_tool(name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    normalized_args = dict(args or {})
    if name not in READ_ONLY_TOOL_SPECS:
        raise ValueError(f"unknown tool '{name}'")

    if name == "list_files":
        path = str(normalized_args.get("path", ".")).strip()
        if not path:
            raise ValueError("path must not be empty")
        normalized_args["path"] = path
        normalized_args["ref"] = str(normalized_args.get("ref", "main")).strip() or "main"
        return normalized_args

    if name == "read_file":
        path = str(normalized_args.get("path", "")).strip()
        if not path:
            raise ValueError("path must not be empty")
        start = int(normalized_args.get("start", 1))
        end = int(normalized_args.get("end", 200))
        if start < 1 or end < start:
            raise ValueError("invalid line range")
        normalized_args["path"] = path
        normalized_args["start"] = start
        normalized_args["end"] = end
        normalized_args["ref"] = str(normalized_args.get("ref", "main")).strip() or "main"
        return normalized_args

    if name == "search":
        pattern = str(normalized_args.get("pattern", "")).strip()
        path = str(normalized_args.get("path", ".")).strip()
        if not pattern:
            raise ValueError("pattern must not be empty")
        if not path:
            raise ValueError("path must not be empty")
        normalized_args["pattern"] = pattern
        normalized_args["path"] = path
        normalized_args["ref"] = str(normalized_args.get("ref", "main")).strip() or "main"
        return normalized_args

    if name == "get_recent_commits":
        limit = int(normalized_args.get("limit", 10))
        if limit < 1 or limit > 50:
            raise ValueError("limit must be in [1, 50]")
        normalized_args["limit"] = limit
        return normalized_args

    return normalized_args
