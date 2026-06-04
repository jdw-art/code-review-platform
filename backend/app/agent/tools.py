from __future__ import annotations

from typing import Any


TOOL_SPECS: dict[str, dict[str, Any]] = {
    "list_files": {
        "schema": {"path": "str='.'"},
        "description": "List pure repository paths in the locked branch, returning up to 200 paths.",
        "risky": False,
    },
    "read_file": {
        "schema": {"path": "str", "start": "int=1", "end": "int=200"},
        "description": "Read numbered lines only from a UTF-8 file in the locked branch, up to 200 lines per call.",
        "risky": False,
    },
    "search_code": {
        "schema": {"query": "str", "path": "str='.'"},
        "description": "Run a case-insensitive substring search in the locked branch, returning path:line:text rows for up to 100 matches.",
        "risky": False,
    },
    "read_project_doc": {
        "schema": {"name": "str"},
        "description": "Read a project doc excerpt from the locked branch snapshot. Available doc names are exposed by the gateway at runtime.",
        "risky": False,
    },
    "get_change_summary": {
        "schema": {"external_id": "str"},
        "description": "Read PR/MR summary.",
        "risky": False,
    },
    "list_commits": {
        "schema": {"external_id": "str"},
        "description": "List commits for PR/MR.",
        "risky": False,
    },
    "list_comment_threads": {
        "schema": {"external_id": "str"},
        "description": "List PR/MR comment threads.",
        "risky": False,
    },
    "get_diff_overview": {
        "schema": {"external_id": "str"},
        "description": "Read diff overview for PR/MR.",
        "risky": False,
    },
}


def sorted_tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "schema": TOOL_SPECS[name]["schema"],
            "description": TOOL_SPECS[name]["description"],
            "risky": TOOL_SPECS[name]["risky"],
        }
        for name in sorted(TOOL_SPECS)
    ]
