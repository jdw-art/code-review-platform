from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any


WORKING_FILE_LIMIT = 8
EPISODIC_NOTE_LIMIT = 12
FILE_SUMMARY_LIMIT = 6


def default_memory_state() -> dict[str, Any]:
    return {
        "working": {
            "task_summary": "",
            "recent_files": [],
        },
        "episodic_notes": [],
        "file_summaries": {},
        "task": "",
        "files": [],
        "notes": [],
        "next_note_index": 0,
    }


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _clip(text: str, limit: int) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def _tokenize(text: Any) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_]+", str(text))}


def _parse_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_note(note: Any, index: int) -> dict[str, Any]:
    if isinstance(note, dict):
        text = _clip(str(note.get("text", "")).strip(), 500)
        tags = [
            str(tag).strip()
            for tag in _ensure_list(note.get("tags", []))
            if str(tag).strip()
        ]
        source = str(note.get("source", "")).strip()
        created_at = str(note.get("created_at", "")).strip() or _utc_now_iso()
        note_index = _safe_int(note.get("note_index"), default=index)
        kind = str(note.get("kind", "episodic")).strip() or "episodic"
        return {
            "text": text,
            "tags": _dedupe_preserve_order(tags),
            "source": source,
            "created_at": created_at,
            "note_index": note_index,
            "kind": kind,
        }

    text = _clip(str(note).strip(), 500)
    return {
        "text": text,
        "tags": [],
        "source": "",
        "created_at": _utc_now_iso(),
        "note_index": index,
        "kind": "episodic",
    }


def _normalize_file_summary(summary: Any) -> dict[str, Any] | None:
    if isinstance(summary, dict):
        text = _clip(str(summary.get("summary", "")).strip(), 500)
        branch = str(summary.get("branch", "")).strip()
        head_sha = str(summary.get("head_sha", "")).strip()
        file_version = str(summary.get("file_version", summary.get("freshness", ""))).strip()
        updated_at = (
            str(summary.get("updated_at", summary.get("created_at", ""))).strip()
            or _utc_now_iso()
        )
        source = str(summary.get("source", "")).strip()
    else:
        text = _clip(str(summary).strip(), 500)
        branch = ""
        head_sha = ""
        file_version = ""
        updated_at = _utc_now_iso()
        source = ""

    if not text:
        return None
    return {
        "summary": text,
        "branch": branch,
        "head_sha": head_sha,
        "file_version": file_version,
        "updated_at": updated_at,
        "source": source,
    }


def _extract_file_version(snapshot_entry: Any) -> str:
    if isinstance(snapshot_entry, dict):
        return str(snapshot_entry.get("file_version", "")).strip()
    if snapshot_entry in (None, ""):
        return ""
    return str(snapshot_entry).strip()


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_memory_state(state: dict[str, Any] | None) -> dict[str, Any]:
    normalized = deepcopy(state) if isinstance(state, dict) else default_memory_state()

    working = normalized.get("working")
    if not isinstance(working, dict):
        working = {}
    task_summary = _clip(str(working.get("task_summary", normalized.get("task", ""))).strip(), 300)
    recent_files = [
        str(path).strip()
        for path in _ensure_list(working.get("recent_files", normalized.get("files", [])))
        if str(path).strip()
    ]
    working["task_summary"] = task_summary
    working["recent_files"] = _dedupe_preserve_order(recent_files)[-WORKING_FILE_LIMIT:]
    normalized["working"] = working

    episodic_notes = normalized.get("episodic_notes")
    if not isinstance(episodic_notes, list):
        episodic_notes = _ensure_list(normalized.get("notes", []))
    normalized_notes = [
        _normalize_note(note, index)
        for index, note in enumerate(episodic_notes)
        if str(note).strip()
    ][-EPISODIC_NOTE_LIMIT:]
    normalized["episodic_notes"] = normalized_notes

    raw_file_summaries = normalized.get("file_summaries")
    if not isinstance(raw_file_summaries, dict):
        raw_file_summaries = {}
    file_summaries: dict[str, dict[str, Any]] = {}
    for path, summary in raw_file_summaries.items():
        file_path = str(path).strip()
        if not file_path:
            continue
        normalized_summary = _normalize_file_summary(summary)
        if normalized_summary is None:
            continue
        file_summaries[file_path] = normalized_summary
    normalized["file_summaries"] = file_summaries

    next_note_index = normalized.get("next_note_index", 0)
    if not isinstance(next_note_index, int) or next_note_index < 0:
        next_note_index = 0
    max_index = max((int(note.get("note_index", 0)) for note in normalized_notes), default=-1)
    normalized["next_note_index"] = max(next_note_index, max_index + 1)

    normalized["task"] = working["task_summary"]
    normalized["files"] = list(working["recent_files"])
    normalized["notes"] = [note["text"] for note in normalized_notes]
    return normalized


def invalidate_stale_file_summaries(
    memory_state: dict[str, Any] | None,
    current_versions: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    state = normalize_memory_state(memory_state)
    invalidated: list[str] = []

    for path, summary in list(state["file_summaries"].items()):
        if path not in current_versions:
            invalidated.append(path)
            state["file_summaries"].pop(path, None)
            continue
        current_file_version = _extract_file_version(current_versions.get(path))
        if not current_file_version:
            continue
        if summary.get("file_version", "") == current_file_version:
            continue
        invalidated.append(path)
        state["file_summaries"].pop(path, None)

    return state, invalidated


def select_relevant_memory(
    memory_state: dict[str, Any] | None,
    query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    state = normalize_memory_state(memory_state)
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    ranked: list[tuple[tuple[int, int, float, int], dict[str, Any]]] = []
    for note in state["episodic_notes"]:
        note_tags = {tag.lower() for tag in note.get("tags", [])}
        note_tokens = _tokenize(note.get("text", "")) | _tokenize(note.get("source", "")) | note_tags
        exact_tag_match = int(bool(query_tokens & note_tags))
        keyword_overlap = len(query_tokens & note_tokens)
        if exact_tag_match == 0 and keyword_overlap == 0:
            continue
        recency = _parse_timestamp(note.get("created_at"))
        note_index = int(note.get("note_index", 0))
        ranked.append(((exact_tag_match, keyword_overlap, recency, note_index), note))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [note for _, note in ranked[:limit]]


def render_memory_text(memory_state: dict[str, Any] | None) -> str:
    state = normalize_memory_state(memory_state)
    lines = [
        "Memory:",
        f"- task: {state['working']['task_summary'] or '-'}",
        f"- recent_files: {', '.join(state['working']['recent_files']) or '-'}",
    ]

    summaries: list[str] = []
    for path in state["working"]["recent_files"][:FILE_SUMMARY_LIMIT]:
        summary = state["file_summaries"].get(path)
        if not summary:
            continue
        summaries.append(f"- {path}: {summary['summary']}")
    if summaries:
        lines.append("- file_summaries:")
        lines.extend(f"  {item}" for item in summaries)
    else:
        lines.append("- file_summaries: -")

    lines.append(f"- episodic_notes: {len(state['episodic_notes'])}")
    return "\n".join(lines)
