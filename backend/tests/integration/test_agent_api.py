from __future__ import annotations

from collections import deque
from sqlalchemy import select

from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.run_service import FakeModelClient
from app.db.models import (
    AgentArtifact,
    AgentMessage,
    AgentRun,
    AgentRunEvent,
    AgentSession,
    Project,
)
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


def test_create_repo_agent_session(authenticated_superuser_client, db_session, monkeypatch) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project",
        platform_type="github",
        repo_url="https://github.com/acme/repo-agent",
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/repo-agent"},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "主分支仓库助手", "branch": "main"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project.id
    assert body["branch"] == "main"
    assert body["status"] == "active"

    stored = db_session.scalar(select(AgentSession).where(AgentSession.id == body["id"]))
    assert stored is not None
    assert stored.project_id == project.id
    assert stored.branch == "main"


def test_create_repo_agent_message_persists_user_message(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-msg",
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

    response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == session_id
    assert body["role"] == "user"
    assert body["status"] == "completed"
    assert body["sequence"] == 1

    stored = db_session.scalar(select(AgentMessage).where(AgentMessage.id == body["id"]))
    assert stored is not None
    assert stored.session_id == session_id
    assert stored.content == "这个仓库是做什么的？"

    assistant = db_session.scalar(
        select(AgentMessage).where(
            AgentMessage.session_id == session_id,
            AgentMessage.role == "assistant",
        )
    )
    assert assistant is not None
    assert assistant.run_id is not None
    assert "README 表明" in assistant.content

    run = db_session.scalar(select(AgentRun).where(AgentRun.id == assistant.run_id))
    assert run is not None
    assert run.status == "completed"
    assert run.tool_steps == 1
    assert run.last_tool == "read_file"
    assert run.workspace_fingerprint
    assert run.runtime_identity_hash
    assert run.prompt_metadata["prefix"]
    assert run.prompt_metadata["memory"].startswith("Memory:")
    assert run.prompt_metadata["current_request"] == "这个仓库是做什么的？"

    events = db_session.scalars(
        select(AgentRunEvent)
        .where(AgentRunEvent.run_id == run.id)
        .order_by(AgentRunEvent.sequence.asc())
    ).all()
    assert [event.event_type for event in events] == [
        "run_started",
        "snapshot_resolved",
        "prompt_built",
        "tool_called",
        "tool_result",
        "prompt_built",
        "assistant_delta",
        "final_answer",
    ]

    artifacts = db_session.scalars(
        select(AgentArtifact).where(AgentArtifact.run_id == run.id)
    ).all()
    assert len(artifacts) == 4
    assert [artifact.artifact_type for artifact in artifacts] == [
        "prompt_context",
        "memory_delta",
        "run_report",
        "snapshot_summary",
    ]

    stored_session = db_session.scalar(select(AgentSession).where(AgentSession.id == session_id))
    assert stored_session is not None
    assert stored_session.last_head_sha == "sha-1"
    assert stored_session.last_workspace_fingerprint
    assert stored_session.last_runtime_identity_hash
    assert stored_session.memory_state["working"]["recent_files"] == ["README.md"]


def test_create_repo_agent_message_relocks_session_before_persisting_assistant_message(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-lock",
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

    lock_calls: deque[tuple[int, int]] = deque()
    original = AgentSessionService._get_session_for_update_or_404

    def tracked_lock(self, *, project_id: int, session_id: int):
        lock_calls.append((project_id, session_id))
        return original(self, project_id=project_id, session_id=session_id)

    monkeypatch.setattr(AgentSessionService, "_get_session_for_update_or_404", tracked_lock)

    response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )

    assert response.status_code == 201
    assert list(lock_calls) == [
        (project.id, session_id),
        (project.id, session_id),
    ]


def test_create_repo_agent_message_includes_previous_round_history_in_later_prompt(
    authenticated_superuser_client,
    db_session,
    monkeypatch,
) -> None:
    _patch_agent_runtime(monkeypatch)
    project = Project(
        name="Repo Agent Project",
        key="repo-agent-project-history",
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

    first_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "这个仓库是做什么的？"},
    )
    assert first_response.status_code == 201

    second_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions/{session_id}/messages",
        json={"content": "刚才说到的入口和认证链路有什么关系？"},
    )
    assert second_response.status_code == 201

    runs = db_session.scalars(
        select(AgentRun)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.id.asc())
    ).all()
    assert len(runs) == 2

    first_history = str(runs[0].prompt_metadata.get("history") or "")
    second_history = str(runs[1].prompt_metadata.get("history") or "")

    assert len(second_history) > len(first_history)
    assert "User: 这个仓库是做什么的？" in second_history
    assert "Assistant: README 表明这个仓库提供 Repo Agent 能力。" in second_history
