from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import default_memory_state
from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.run_service import FakeModelClient, RunService
from app.agent.snapshot_service import SnapshotService


def test_run_service_executes_tool_then_returns_final() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Repo Agent\n用途：说明仓库入口。\n"},
        recent_commits={"main": ["c1 init"]},
    )
    model = FakeModelClient(
        outputs=[
            '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":20}}</tool>',
            "<final>README 表明这个仓库提供 Repo Agent 能力。</final>",
        ]
    )
    service = RunService(
        model_client=model,
        context_manager=ContextManager(total_budget=2000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=default_memory_state(),
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(user_message="这个仓库是做什么的？")

    assert result["status"] == "completed"
    assert result["final_answer"].startswith("README 表明")
    assert result["tool_steps"] == 1
    assert result["last_tool"] == "read_file"
    assert result["events"][0]["event_type"] == "run_started"
    assert result["events"][1]["event_type"] == "snapshot_resolved"
    assert result["events"][2]["event_type"] == "prompt_built"
    assert result["events"][3]["event_type"] == "tool_called"
    assert result["events"][4]["event_type"] == "tool_result"
    assert result["events"][-2]["event_type"] == "assistant_delta"
    assert result["events"][-2]["payload"]["delta"].startswith("README 表明")
    assert result["events"][-1]["event_type"] == "final_answer"
    assert result["completion_metadata"]["model"] == "fake-model"
    assert result["memory_state"]["working"]["recent_files"] == ["README.md"]
    assert result["prompt_metadata"]["prefix"]
    raw_prefix = result["prompt_metadata"]["raw_sections"]["prefix"]
    assert "Return exactly one <tool>...</tool> or one <final>...</final>." in raw_prefix
    assert '<tool>{"name":"list_files","args":{"path":"."}}</tool>' in raw_prefix
    assert "When you already have enough evidence to answer" in raw_prefix
    assert result["prompt_metadata"]["memory"].startswith("Memory:")
    assert result["prompt_metadata"]["current_request"] == "这个仓库是做什么的？"
    artifact_types = [artifact["artifact_type"] for artifact in result["artifacts"]]
    assert artifact_types == [
        "prompt_context",
        "memory_delta",
        "run_report",
        "snapshot_summary",
    ]
    assert result["artifacts"][0]["content"]["current_request"] == "这个仓库是做什么的？"
    assert result["artifacts"][1]["content"]["before"]["working"]["recent_files"] == []
    assert result["artifacts"][1]["content"]["after"]["working"]["recent_files"] == ["README.md"]


def test_run_service_uses_shared_llm_client_when_model_client_missing(monkeypatch) -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-2"},
        files={("main", "README.md"): "# Repo Agent\n"},
        recent_commits={"main": ["c1 init"]},
    )
    calls: list[list[dict[str, str]]] = []

    class StubClient:
        def completions(self, *, messages: list[dict[str, str]]) -> str:
            calls.append(messages)
            return "<final>共享 LLM 客户端已接入。</final>"

    monkeypatch.setattr(
        "app.agent.run_service.load_llm_config",
        lambda default_provider="openai": type(
            "Cfg",
            (),
            {
                "provider": "openai",
                "model": "gpt-5.4",
                "api_key": "test-key",
                "api_base_url": "https://example.com/v1",
                "required_env": (),
            },
        )(),
    )
    monkeypatch.setattr("app.agent.run_service.build_llm_client", lambda config: StubClient())

    service = RunService(
        model_client=None,
        context_manager=ContextManager(total_budget=2000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=default_memory_state(),
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(user_message="这个仓库是做什么的？")

    assert result["status"] == "completed"
    assert result["completion_metadata"]["provider"] == "openai"
    assert result["completion_metadata"]["model"] == "gpt-5.4"
    assert calls


def test_run_service_records_memory_invalidation_when_file_version_changes() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-2"},
        files={("main", "README.md"): "# New Title\n"},
        recent_commits={"main": ["c2 update"]},
    )
    memory_state = default_memory_state()
    memory_state["file_summaries"] = {
        "README.md": {
            "summary": "old summary",
            "branch": "main",
            "head_sha": "sha-1",
            "file_version": "old-version",
            "updated_at": "2026-06-04T00:00:00+00:00",
            "source": "tool:read_file",
        }
    }
    service = RunService(
        model_client=FakeModelClient(outputs=["<final>done</final>"]),
        context_manager=ContextManager(total_budget=2000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=memory_state,
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(user_message="hello")

    assert any(event["event_type"] == "memory_invalidated" for event in result["events"])


def test_run_service_carries_forward_session_history_into_prompt_metadata() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-3"},
        files={},
        recent_commits={"main": ["c3 docs"]},
    )
    service = RunService(
        model_client=FakeModelClient(outputs=["<final>继续分析入口与认证关系。</final>"]),
        context_manager=ContextManager(total_budget=2000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=default_memory_state(),
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(
        user_message="刚才说到的入口和认证链路有什么关系？",
        history=(
            "User: 这个仓库的后端入口在哪里？\n"
            "Assistant: 后端入口在 api.py。"
        ),
    )

    assert result["status"] == "completed"
    assert "这个仓库的后端入口在哪里" in result["prompt_metadata"]["history"]
    assert "后端入口在 api.py" in result["prompt_metadata"]["history"]


def test_run_service_retries_premature_final_that_requests_file_read() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-4"},
        files={("main", "api.py"): "print('hello')\n"},
        recent_commits={"main": ["c4 init"]},
    )
    model = FakeModelClient(
        outputs=[
            "<final>我还不能确定，需先读入口文件。请让我查看 `api.py`。</final>",
            '<tool>{"name":"read_file","args":{"path":"api.py","start":1,"end":20}}</tool>',
            "<final>入口文件已经读取，后端入口就在 api.py。</final>",
        ]
    )
    service = RunService(
        model_client=model,
        context_manager=ContextManager(total_budget=4000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=default_memory_state(),
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(user_message="这个仓库的后端入口在哪里？")

    assert result["status"] == "completed"
    assert result["final_answer"] == "入口文件已经读取，后端入口就在 api.py。"
    assert result["tool_steps"] == 1
    assert any(
        event["event_type"] == "model_retry"
        and "Do not ask the user for permission" in str(event["payload"].get("notice", ""))
        for event in result["events"]
    )


def test_run_service_records_raw_response_preview_for_retry_events() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-5"},
        files={("main", "api.py"): "print('hello')\n"},
        recent_commits={"main": ["c5 init"]},
    )
    malformed = (
        '<tool>{"name":"read_file","args":{"path":"api.py","start":1,"end":20}}</tool>'
        "\n"
        "<final>done</final>"
    )
    service = RunService(
        model_client=FakeModelClient(
            outputs=[
                malformed,
                "<final>最终答案。</final>",
            ]
        ),
        context_manager=ContextManager(total_budget=4000),
        snapshot_service=SnapshotService(provider=provider),
        memory_state=default_memory_state(),
        provider=provider,
        branch="main",
        project_id=1,
        platform_type="github",
        default_branch="main",
    )

    result = service.run(user_message="这个仓库的后端入口在哪里？")

    retry_events = [
        event for event in result["events"] if event["event_type"] == "model_retry"
    ]
    assert result["status"] == "completed"
    assert retry_events
    assert "multiple top-level actions" in str(retry_events[0]["payload"].get("notice", ""))
    assert retry_events[0]["payload"]["raw_response_preview"] == malformed.replace("\n", " ")
