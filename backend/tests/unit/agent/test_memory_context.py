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
