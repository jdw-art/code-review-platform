from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import default_memory_state
from app.agent.workspace import WorkspaceContext


def test_default_memory_state_matches_pico_shape() -> None:
    state = default_memory_state()

    assert state["working"] == {"task_summary": "", "recent_files": []}
    assert state["episodic_notes"] == []
    assert state["file_summaries"] == {}
    assert state["task"] == ""
    assert state["files"] == []
    assert state["notes"] == []
    assert state["next_note_index"] == 0


def test_context_manager_keeps_current_request_and_workspace() -> None:
    workspace = WorkspaceContext(
        project_id=1,
        project_name="Demo",
        platform_type="github",
        repo_url="https://example.com/demo.git",
        ref="main",
        head_sha="abc123",
        fingerprint="fp-demo",
        overview={"readme": "Demo README"},
        recent_commits=[],
    )
    manager = ContextManager(
        workspace_text=workspace.text(),
        memory_state=default_memory_state(),
        history=[{"role": "user", "content": "上一轮问认证"}],
    )

    prompt, metadata = manager.build("那权限在哪里校验？")

    assert "Workspace:" in prompt
    assert "Demo README" in prompt
    assert "上一轮问认证" in prompt
    assert "那权限在哪里校验？" in prompt
    assert metadata["prompt_chars"] == len(prompt)


def test_context_manager_keeps_latest_history_when_budget_is_small() -> None:
    manager = ContextManager(
        workspace_text="Workspace:\n- name: demo",
        memory_state=default_memory_state(),
        history=[
            {"role": "user", "content": "第一轮：最旧的问题"},
            {"role": "assistant", "content": "第一轮：最旧的回答"},
            {"role": "user", "content": "第二轮：最新的问题"},
            {"role": "assistant", "content": "第二轮：最新的回答"},
        ],
        section_budgets={"history": 60},
    )

    prompt, _ = manager.build("第三轮：继续追问")

    assert "第二轮：最新的回答" in prompt
    assert "第一轮：最旧的问题" not in prompt


def test_context_manager_renders_file_summaries_and_notes() -> None:
    state = default_memory_state()
    state["episodic_notes"] = ["note-a"]
    state["file_summaries"] = {"backend/app/main.py": "FastAPI entrypoint"}
    state["notes"] = ["project convention: keep routes thin"]

    manager = ContextManager(
        workspace_text="Workspace:\n- name: demo",
        memory_state=state,
        history=[],
    )

    prompt, metadata = manager.build("入口在哪？")

    assert "note-a" in prompt
    assert "backend/app/main.py: FastAPI entrypoint" in prompt
    assert "project convention: keep routes thin" in prompt
    assert "relevant_memory" in metadata["sections"]


def test_workspace_fingerprint_ignores_noisy_fields() -> None:
    base_payload = {
        "project_id": 1,
        "project_name": "Demo",
        "platform_type": "github",
        "repo_url": "https://example.com/demo.git",
        "ref": "main",
        "head_sha": "abc123",
        "snapshot_id": 8,
        "tool_signature": "tools-v1",
        "settings_hash": "settings-v1",
    }

    fingerprint_a = WorkspaceContext.build_fingerprint(
        {
            **base_payload,
            "overview": {"readme": "v1"},
            "recent_commits": [{"id": "1", "message": "A"}],
        }
    )
    fingerprint_b = WorkspaceContext.build_fingerprint(
        {
            **base_payload,
            "overview": {"readme": "v2"},
            "recent_commits": [{"id": "2", "message": "B"}],
        }
    )

    assert fingerprint_a == fingerprint_b
