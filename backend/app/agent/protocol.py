from __future__ import annotations

import json
import re
from typing import Any


_TOOL_OPEN = "<tool>"
_TOOL_CLOSE = "</tool>"
_FINAL_OPEN = "<final>"
_FINAL_CLOSE = "</final>"
_TOP_LEVEL_ACTION_RE = re.compile(r"(<tool>.*?</tool>|<final>.*?</final>)", re.DOTALL)


def parse_agent_response(raw: str) -> tuple[str, Any]:
    text = str(raw).strip()
    if not text:
        return "retry", retry_notice("model returned an empty response")

    if text.startswith(_TOOL_OPEN) and text.endswith(_TOOL_CLOSE):
        return _parse_tool_text(text)

    if text.startswith(_FINAL_OPEN) and text.endswith(_FINAL_CLOSE):
        return _parse_final_text(text)

    normalized_tool = _normalize_repeated_identical_tools(text)
    if normalized_tool is not None:
        return normalized_tool

    if _contains_tag(text, "tool") and _contains_tag(text, "final"):
        return "retry", retry_notice("model returned multiple top-level actions; emit exactly one top-level action")
    if _contains_tag(text, "tool") or _contains_tag(text, "final"):
        return "retry", retry_notice("model returned text outside the top-level tag")
    return "retry", retry_notice("model returned malformed tool output")


def retry_notice(problem: str | None = None) -> str:
    prefix = "Runtime notice"
    if problem:
        prefix += f": {problem}"
    else:
        prefix += ": model returned malformed tool output"
    return (
        f"{prefix}. Reply with a valid <tool> call or a <final> answer using exactly one top-level action. "
        'Use the read-only online protocol: <tool>{"name":"tool_name","args":{...}}</tool> '
        "or <final>your answer</final>."
    )


def _parse_tool_payload(body: str) -> tuple[str, Any]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        if re.search(r"</tool>\s*<tool>", body):
            return "retry", retry_notice(
                "model returned multiple top-level actions; emit exactly one top-level action"
            )
        return "retry", retry_notice("model returned malformed tool JSON")
    if not isinstance(payload, dict):
        return "retry", retry_notice("tool payload must be a JSON object")

    name = str(payload.get("name", "")).strip()
    if not name:
        return "retry", retry_notice("tool payload is missing a tool name")

    args = payload.get("args")
    if not isinstance(args, dict):
        return "retry", retry_notice("tool payload args must be a JSON object")

    return "tool", {"name": name, "args": args}


def _contains_tag(text: str, tag: str) -> bool:
    return f"<{tag}" in text or f"</{tag}>" in text


def _parse_tool_text(text: str) -> tuple[str, Any]:
    body = text[len(_TOOL_OPEN) : -len(_TOOL_CLOSE)]
    return _parse_tool_payload(body)


def _parse_final_text(text: str) -> tuple[str, Any]:
    body = text[len(_FINAL_OPEN) : -len(_FINAL_CLOSE)]
    if re.search(r"</final>\s*<final>", body):
        return "retry", retry_notice(
            "model returned multiple top-level actions; emit exactly one top-level action"
        )
    final = body.strip()
    if not final:
        return "retry", retry_notice("model must return a non-empty <final> answer")
    return "final", final


def _normalize_repeated_identical_tools(text: str) -> tuple[str, Any] | None:
    actions = _parse_top_level_actions(text)
    if actions is None:
        return None

    tool_bodies = [body for kind, body in actions if kind == "tool"]
    final_bodies = [body for kind, body in actions if kind == "final"]
    if len(tool_bodies) < 2 or len(final_bodies) > 1:
        return None

    parsed_tools: list[dict[str, Any]] = []
    for body in tool_bodies:
        kind, payload = _parse_tool_payload(body)
        if kind != "tool":
            return None
        parsed_tools.append(payload)

    first_tool = parsed_tools[0]
    if any(tool != first_tool for tool in parsed_tools[1:]):
        return None

    if final_bodies:
        final_kind, _ = _parse_final_text(f"{_FINAL_OPEN}{final_bodies[0]}{_FINAL_CLOSE}")
        if final_kind != "final":
            return None

    return "tool", first_tool


def _parse_top_level_actions(text: str) -> list[tuple[str, str]] | None:
    actions: list[tuple[str, str]] = []
    cursor = 0
    for match in _TOP_LEVEL_ACTION_RE.finditer(text):
        if text[cursor : match.start()].strip():
            return None
        token = match.group(0)
        if token.startswith(_TOOL_OPEN):
            actions.append(("tool", token[len(_TOOL_OPEN) : -len(_TOOL_CLOSE)]))
        else:
            actions.append(("final", token[len(_FINAL_OPEN) : -len(_FINAL_CLOSE)]))
        cursor = match.end()

    if not actions or text[cursor:].strip():
        return None
    return actions
