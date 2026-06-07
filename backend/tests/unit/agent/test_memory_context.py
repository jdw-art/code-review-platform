from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import (
    default_memory_state,
    invalidate_stale_file_summaries,
    normalize_memory_state,
)


def test_default_memory_state_preserves_pico_shape() -> None:
    state = default_memory_state()

    assert state == {
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


def test_invalidate_stale_file_summaries_only_removes_changed_files() -> None:
    state = default_memory_state()
    state["file_summaries"] = {
        "stable.py": {
            "summary": "stable summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "same-hash",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        },
        "changed.py": {
            "summary": "changed summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "old-hash",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        },
    }

    updated_state, invalidated = invalidate_stale_file_summaries(
        state,
        {
            "stable.py": {"file_version": "same-hash", "head_sha": "new-head"},
            "changed.py": {"file_version": "new-hash", "head_sha": "new-head"},
        },
    )

    assert invalidated == ["changed.py"]
    assert updated_state["file_summaries"] == {
        "stable.py": {
            "summary": "stable summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "same-hash",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        }
    }


def test_normalize_memory_state_preserves_file_summary_metadata() -> None:
    state = normalize_memory_state(
        {
            "file_summaries": {
                "backend/app/agent/protocol.py": {
                    "summary": "protocol summary",
                    "branch": "feature/task-2",
                    "head_sha": "abc123",
                    "file_version": "blob-1",
                    "updated_at": "2026-06-04T08:00:00+00:00",
                    "source": "repo_snapshot",
                }
            }
        }
    )

    assert state["file_summaries"] == {
        "backend/app/agent/protocol.py": {
            "summary": "protocol summary",
            "branch": "feature/task-2",
            "head_sha": "abc123",
            "file_version": "blob-1",
            "updated_at": "2026-06-04T08:00:00+00:00",
            "source": "repo_snapshot",
        }
    }


def test_invalidate_stale_file_summaries_removes_missing_paths() -> None:
    state = default_memory_state()
    state["file_summaries"] = {
        "deleted.py": {
            "summary": "old summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "blob-1",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        }
    }

    updated_state, invalidated = invalidate_stale_file_summaries(state, {})

    assert invalidated == ["deleted.py"]
    assert updated_state["file_summaries"] == {}


def test_invalidate_stale_file_summaries_keeps_summary_when_only_head_sha_changes() -> None:
    state = default_memory_state()
    state["file_summaries"] = {
        "stable.py": {
            "summary": "stable summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "same-hash",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        }
    }

    updated_state, invalidated = invalidate_stale_file_summaries(
        state,
        {
            "stable.py": {"file_version": "same-hash", "head_sha": "new-head"},
        },
    )

    assert invalidated == []
    assert updated_state["file_summaries"]["stable.py"]["head_sha"] == "old-head"


def test_invalidate_stale_file_summaries_keeps_summary_when_file_version_is_unknown() -> None:
    state = default_memory_state()
    state["file_summaries"] = {
        "stable.py": {
            "summary": "stable summary",
            "branch": "feature/test",
            "head_sha": "old-head",
            "file_version": "same-hash",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "repo_snapshot",
        }
    }

    updated_state, invalidated = invalidate_stale_file_summaries(
        state,
        {
            "stable.py": {"head_sha": "new-head"},
        },
    )

    assert invalidated == []
    assert updated_state["file_summaries"]["stable.py"]["file_version"] == "same-hash"


def test_normalize_memory_state_falls_back_when_note_index_is_invalid() -> None:
    state = normalize_memory_state(
        {
            "episodic_notes": [
                {
                    "text": "remember this",
                    "note_index": "abc",
                }
            ]
        }
    )

    assert state["episodic_notes"][0]["note_index"] == 0


def test_context_manager_keeps_current_request_when_over_budget() -> None:
    manager = ContextManager(
        total_budget=140,
        section_budgets={
            "prefix": 60,
            "memory": 50,
            "relevant_memory": 50,
            "history": 60,
        },
        section_floors={
            "prefix": 10,
            "memory": 10,
            "relevant_memory": 10,
            "history": 10,
        },
    )

    prompt, metadata = manager.build(
        prefix="P" * 60,
        memory="M" * 50,
        relevant_memory="R" * 50,
        history="H" * 60,
        current_request="Current user request:\nkeep this request intact",
    )

    assert prompt.split("\n\n")[-1] == "Current user request:\nkeep this request intact"
    assert metadata["section_order"] == [
        "prefix",
        "memory",
        "relevant_memory",
        "history",
        "current_request",
    ]
    assert metadata["reduction_order"] == [
        "relevant_memory",
        "history",
        "memory",
        "prefix",
    ]
    assert metadata["sections"]["current_request"]["rendered_chars"] == len(
        "Current user request:\nkeep this request intact"
    )


def test_context_manager_preserves_history_tail_when_clipped() -> None:
    manager = ContextManager(
        total_budget=200,
        section_budgets={
            "prefix": 20,
            "memory": 20,
            "relevant_memory": 20,
            "history": 18,
        },
    )

    prompt, _ = manager.build(
        prefix="prefix",
        memory="memory",
        relevant_memory="relevant",
        history="old-context -> newer-context -> latest-context",
        current_request="Current request",
    )

    history_section = prompt.split("\n\n")[3]
    assert history_section.startswith("...")
    assert "latest-context" in history_section
    assert "old-context" not in history_section


def test_context_manager_exposes_rendered_prompt_sections_in_metadata() -> None:
    manager = ContextManager(total_budget=600)

    _, metadata = manager.build(
        prefix="Prefix section",
        memory="Memory section",
        relevant_memory="Relevant memory section",
        history="History section",
        current_request="Current request section",
    )

    assert metadata["prefix"] == "Prefix section"
    assert metadata["memory"] == "Memory section"
    assert metadata["relevant_memory"] == "Relevant memory section"
    assert metadata["history"] == "History section"
    assert metadata["current_request"] == "Current request section"
    assert metadata["raw_sections"]["prefix"] == "Prefix section"
    assert metadata["rendered_sections"]["history"] == "History section"
