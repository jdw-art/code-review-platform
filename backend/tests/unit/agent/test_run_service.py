from __future__ import annotations

from sqlalchemy import select

from app.agent.snapshot_service import RepositorySnapshotService
from app.db.models import AgentRunEvent, Project


class FakeRepositoryProvider:
    def __init__(self) -> None:
        self.read_calls: list[dict[str, object]] = []

    def get_head_sha(self, *, ref: str) -> str:
        assert ref == "main"
        return "sha-main"

    def get_file_tree(self, *, ref: str) -> list[dict[str, str]]:
        assert ref == "main"
        return [
            {"path": "README.md", "type": "file"},
            {"path": "backend/app/main.py", "type": "file"},
        ]

    def get_snapshot_overview(self, *, ref: str) -> dict[str, str]:
        assert ref == "main"
        return {"readme": "AI Code Reviewer"}

    def get_recent_commit_records(self, *, limit: int) -> list[dict[str, str]]:
        assert limit == 10
        return [{"id": "c1", "message": "feat: init"}]

    def list_files(self, *, path: str, ref: str) -> str:
        return f"{path}\nREADME.md\nbackend/app/main.py"

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        self.read_calls.append(
            {"path": path, "start": start, "end": end, "ref": ref}
        )
        return "line 1\nline 2\nline 3"

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        return f"search:{pattern}:{path}:{ref}"

    def get_project_overview(self) -> str:
        return "overview"

    def get_recent_commits(self, *, limit: int) -> str:
        return f"commits:{limit}"


class FakeModelClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[dict[str, object]] = []

    def complete(self, *, prompt: str, metadata: dict[str, object]) -> str:
        self.prompts.append({"prompt": prompt, "metadata": metadata})
        return self.responses.pop(0)


def _create_project(db_session) -> Project:
    project = Project(
        name="Repo Agent Demo",
        key="repo-agent-run",
        platform_type="github",
        repo_url="https://example.com/demo.git",
        default_branch="main",
        review_enabled=True,
        settings={},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _create_session_bundle(db_session):
    from app.services.agent_session_service import AgentSessionService

    provider = FakeRepositoryProvider()
    project = _create_project(db_session)
    snapshot = RepositorySnapshotService(db_session).ensure_ready_snapshot(
        project=project,
        provider=provider,
    )
    session_service = AgentSessionService(db_session)
    agent_session = session_service.create_session(
        project=project,
        title="仓库理解助手",
        created_by=None,
        snapshot=snapshot,
    )
    return project, snapshot, provider, session_service, agent_session


def test_run_service_completes_final_answer(db_session) -> None:
    from app.agent.event_recorder import AgentEventRecorder
    from app.agent.run_service import AgentRunService
    from app.agent.tool_gateway import AgentToolGateway

    _, _, provider, session_service, agent_session = _create_session_bundle(db_session)
    fake_model = FakeModelClient(["Final answer"])
    user_message, assistant_message, run = session_service.create_message_pair_and_run(
        session=agent_session,
        content="这个仓库是干什么的？",
    )
    service = AgentRunService(
        session=db_session,
        model_client=fake_model,
        tool_gateway=AgentToolGateway(provider=provider),
        event_recorder=AgentEventRecorder(db_session),
    )

    completed = service.run(run.id)

    db_session.refresh(assistant_message)
    assert completed.status == "completed"
    assert completed.stop_reason == "final_answer_returned"
    assert assistant_message.content == "Final answer"
    assert user_message.content == "这个仓库是干什么的？"
    assert fake_model.prompts[0]["metadata"]["snapshot_id"] == completed.snapshot_id
    assert "Tools:" in str(fake_model.prompts[0]["prompt"])


def test_run_service_executes_tool_then_completes(db_session) -> None:
    from app.agent.event_recorder import AgentEventRecorder
    from app.agent.run_service import AgentRunService
    from app.agent.tool_gateway import AgentToolGateway

    _, _, provider, session_service, agent_session = _create_session_bundle(db_session)
    fake_model = FakeModelClient(
        [
            '{"tool": {"name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20, "ref": "main"}}}',
            "I found the repo overview in README.md.",
        ]
    )
    user_message, _, run = session_service.create_message_pair_and_run(
        session=agent_session,
        content="先看 README，再总结一下。",
    )
    service = AgentRunService(
        session=db_session,
        model_client=fake_model,
        tool_gateway=AgentToolGateway(provider=provider),
        event_recorder=AgentEventRecorder(db_session),
    )

    completed = service.run(run.id)

    tool_events = db_session.scalars(
        select(AgentRunEvent).where(
            AgentRunEvent.run_id == run.id,
            AgentRunEvent.event_type == "tool_result",
        )
    ).all()
    assert completed.status == "completed"
    assert user_message.content == "先看 README，再总结一下。"
    assert len(tool_events) == 1
    assert tool_events[0].payload["name"] == "read_file"


def test_run_service_stops_at_step_limit(db_session) -> None:
    from app.agent.event_recorder import AgentEventRecorder
    from app.agent.run_service import AgentRunService
    from app.agent.tool_gateway import AgentToolGateway

    _, _, provider, session_service, agent_session = _create_session_bundle(db_session)
    fake_model = FakeModelClient(
        ['{"tool": {"name": "search", "args": {"pattern": "router", "path": ".", "ref": "main"}}}']
    )
    _, _, run = session_service.create_message_pair_and_run(
        session=agent_session,
        content="找一下路由定义。",
    )
    service = AgentRunService(
        session=db_session,
        model_client=fake_model,
        tool_gateway=AgentToolGateway(provider=provider),
        event_recorder=AgentEventRecorder(db_session),
        max_steps=1,
    )

    stopped = service.run(run.id)

    assert stopped.status == "stopped"
    assert stopped.stop_reason == "step_limit_reached"


def test_run_service_persists_updated_memory_state(db_session) -> None:
    from app.agent.event_recorder import AgentEventRecorder
    from app.agent.run_service import AgentRunService
    from app.agent.tool_gateway import AgentToolGateway

    _, _, provider, session_service, agent_session = _create_session_bundle(db_session)
    fake_model = FakeModelClient(
        [
            '{"tool": {"name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20, "ref": "main"}}}',
            "README explains the system.",
        ]
    )
    _, _, run = session_service.create_message_pair_and_run(
        session=agent_session,
        content="读 README 并记录关键文件。",
    )
    service = AgentRunService(
        session=db_session,
        model_client=fake_model,
        tool_gateway=AgentToolGateway(provider=provider),
        event_recorder=AgentEventRecorder(db_session),
    )

    service.run(run.id)
    db_session.refresh(agent_session)

    assert "README.md" in agent_session.memory_state["working"]["recent_files"]
