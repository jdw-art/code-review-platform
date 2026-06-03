from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.agent.repository_provider import RepositoryContentProvider
from app.agent.tools import READ_ONLY_TOOL_SPECS, validate_tool

REDACTED_VALUE = "<redacted>"
SECRET_SHAPED_TEXT_PATTERN = re.compile(
    r"(?i)(\b(api[_ -]?key|token|secret|password|authorization)\b|sk-[A-Za-z0-9_-]{6,})"
)


@dataclass
class ToolExecutionResult:
    name: str
    args: dict[str, Any]
    output: str
    status: str
    cached: bool = False
    error_code: str = ""


class AgentToolGateway:
    def __init__(
        self,
        *,
        provider: RepositoryContentProvider,
        authorize: Callable[[str, dict[str, Any]], None] | None = None,
        output_limit: int = 4000,
    ) -> None:
        self.provider = provider
        self.authorize = authorize or (lambda _name, _args: None)
        self.output_limit = int(output_limit)
        self._cache: dict[str, ToolExecutionResult] = {}

    def execute(
        self,
        name: str,
        args: dict[str, Any] | None,
        *,
        snapshot_id: int,
        history: list[dict[str, Any]],
    ) -> ToolExecutionResult:
        normalized_args = validate_tool(name, args)
        self.authorize(name, normalized_args)

        if self._repeated_tool_call(history, name, normalized_args):
            return ToolExecutionResult(
                name=name,
                args=normalized_args,
                output=f"error: repeated identical tool call for {name}; choose a different tool or return a final answer",
                status="rejected",
                cached=False,
                error_code="repeated_identical_call",
            )

        cache_key = self._cache_key(snapshot_id, name, normalized_args)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return ToolExecutionResult(
                name=cached.name,
                args=cached.args,
                output=cached.output,
                status=cached.status,
                cached=True,
                error_code=cached.error_code,
            )

        raw_output = self._execute_provider_tool(name, normalized_args)
        output = self._clip(self._redact(raw_output))
        result = ToolExecutionResult(
            name=name,
            args=normalized_args,
            output=output,
            status="ok",
        )
        self._cache[cache_key] = result
        return result

    @staticmethod
    def _repeated_tool_call(history: list[dict[str, Any]], name: str, args: dict[str, Any]) -> bool:
        tool_events = [item for item in history if item.get("role") == "tool"]
        if len(tool_events) < 2:
            return False
        recent = tool_events[-2:]
        return all(item.get("name") == name and item.get("args") == args for item in recent)

    @staticmethod
    def _cache_key(snapshot_id: int, name: str, args: dict[str, Any]) -> str:
        payload = {
            "snapshot_id": snapshot_id,
            "tool": name,
            "args": args,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _execute_provider_tool(self, name: str, args: dict[str, Any]) -> str:
        if name == "list_files":
            return self.provider.list_files(path=args["path"], ref=args["ref"])
        if name == "read_file":
            return self.provider.read_file(
                path=args["path"],
                start=args["start"],
                end=args["end"],
                ref=args["ref"],
            )
        if name == "search":
            return self.provider.search(
                pattern=args["pattern"],
                path=args["path"],
                ref=args["ref"],
            )
        if name == "get_project_overview":
            return self.provider.get_project_overview()
        if name == "get_recent_commits":
            return self.provider.get_recent_commits(limit=args["limit"])
        raise ValueError(f"unknown tool '{name}'")

    @staticmethod
    def _redact(text: str) -> str:
        return SECRET_SHAPED_TEXT_PATTERN.sub(REDACTED_VALUE, str(text))

    def _clip(self, text: str) -> str:
        if len(text) <= self.output_limit:
            return text
        return text[: self.output_limit] + f"\n...[truncated {len(text) - self.output_limit} chars]"
