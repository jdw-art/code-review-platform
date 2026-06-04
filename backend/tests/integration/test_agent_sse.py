from __future__ import annotations

from types import SimpleNamespace
import threading

from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.run_service import FakeModelClient
from app.db.models import AgentMessage, AgentRunEvent, Project
from app.services.agent_session_service import AgentSessionService


def _patch_agent_runtime(monkeypatch) -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "# Repo Agent\n用途：说明仓库入口。\n"},
        recent_commits={"main": ["c1 init"]},
    )
    monkeypatch.setattr(
        AgentSessionService,
        "_build_repository_provider",
        lambda self, project: provider,
    )
    monkeypatch.setattr(
        AgentSessionService,
        "_load_llm_config",
        lambda self: type(
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
    monkeypatch.setattr(
        AgentSessionService,
        "_build_model_client",
        lambda self, llm_config: FakeModelClient(
            outputs=[
                '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":20}}</tool>',
                "<final>README 表明这个仓库提供 Repo Agent 能力。</final>",
            ]
        ),
    )


def test_repo_agent_stream_endpoint_returns_sse_headers(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-sse",
        platform_type="github",
        repo_url="https://github.com/acme/repo-agent",
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/repo-agent"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "主分支仓库助手", "branch": "main"},
    )
    session_id = session_response.json()["id"]

    message_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )
    assert message_response.status_code == 201

    response = authenticated_superuser_client.get(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/stream"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: run_started" in response.text
    assert "event: tool_called" in response.text
    assert "event: final_answer" in response.text


def test_repo_agent_stream_receives_events_after_subscription(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-sse-live",
        platform_type="github",
        repo_url="https://github.com/acme/repo-agent",
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/repo-agent"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "主分支仓库助手", "branch": "main"},
    )
    session_id = session_response.json()["id"]

    stream_body: dict[str, str] = {"text": ""}

    def consume_stream() -> None:
        with authenticated_superuser_client.stream(
            "GET",
            f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/stream",
        ) as response:
            assert response.status_code == 200
            chunks: list[str] = []
            for text in response.iter_text():
                chunks.append(text)
            stream_body["text"] = "".join(chunks)

    thread = threading.Thread(target=consume_stream)
    thread.start()

    message_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )
    assert message_response.status_code == 201

    thread.join(timeout=10)
    assert not thread.is_alive()
    assert "event: run_started" in stream_body["text"]
    assert "event: tool_called" in stream_body["text"]
    assert "event: final_answer" in stream_body["text"]


def test_repo_agent_stream_keeps_waiting_while_run_is_still_active(
    db_session,
    monkeypatch,
) -> None:
    service = AgentSessionService(session=db_session)
    call_state = {"count": 0}

    def fake_load_stream_envelopes(*, session_id: int, last_message_id: int, last_event_id: int):
        del session_id, last_message_id, last_event_id
        call_state["count"] += 1
        if call_state["count"] == 1:
            return [
                {
                    "kind": "run_event",
                    "event": "run_started",
                    "sort_at": 0,
                    "sort_id": 1,
                    "data": {
                        "id": 1,
                        "run_id": 1,
                        "session_id": 1,
                        "sequence": 1,
                        "payload": {"branch": "main", "head_sha": "sha-1"},
                        "created_at": "2026-06-04T08:00:00Z",
                    },
                }
            ]
        if call_state["count"] == 45:
            return [
                {
                    "kind": "run_event",
                    "event": "final_answer",
                    "sort_at": 1,
                    "sort_id": 2,
                    "data": {
                        "id": 2,
                        "run_id": 1,
                        "session_id": 1,
                        "sequence": 2,
                        "payload": {"final_answer": "done"},
                        "created_at": "2026-06-04T08:00:10Z",
                    },
                }
            ]
        return []

    monkeypatch.setattr(
        service,
        "_get_session_or_404",
        lambda **kwargs: SimpleNamespace(id=kwargs["session_id"], status="active"),
    )
    monkeypatch.setattr(service, "_load_stream_envelopes", fake_load_stream_envelopes)
    monkeypatch.setattr(
        service,
        "_has_running_run",
        lambda session_id: call_state["count"] < 45,
        raising=False,
    )
    monkeypatch.setattr("app.services.agent_session_service.time.sleep", lambda _: None)

    payload = "".join(service.stream_events(project_id=1, session_id=1))

    assert "event: run_started" in payload
    assert "event: final_answer" in payload


def test_repo_agent_stream_supports_incremental_cursor_subscription(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-sse-cursor",
        platform_type="github",
        repo_url="https://github.com/acme/repo-agent",
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/repo-agent"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "主分支仓库助手", "branch": "main"},
    )
    session_id = session_response.json()["id"]

    first_message = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )
    assert first_message.status_code == 201

    baseline_event_id = db_session.query(AgentRunEvent.id).order_by(AgentRunEvent.id.desc()).first()[0]
    baseline_message_id = db_session.query(AgentMessage.id).order_by(AgentMessage.id.desc()).first()[0]

    second_stream_text: dict[str, str] = {"text": ""}

    def consume_stream() -> None:
        with authenticated_superuser_client.stream(
            "GET",
            (
                f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/stream"
                f"?after_event_id={baseline_event_id}&after_message_id={baseline_message_id}"
            ),
        ) as response:
            assert response.status_code == 200
            chunks: list[str] = []
            for text in response.iter_text():
                chunks.append(text)
            second_stream_text["text"] = "".join(chunks)

    thread = threading.Thread(target=consume_stream)
    thread.start()

    second_message = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "刚才说到的入口和认证链路有什么关系？"},
    )
    assert second_message.status_code == 201

    thread.join(timeout=10)
    assert not thread.is_alive()
    assert "刚才说到的入口和认证链路有什么关系" in second_stream_text["text"]
    assert "这个仓库是做什么的？" not in second_stream_text["text"]
    assert "event: final_answer" in second_stream_text["text"]
