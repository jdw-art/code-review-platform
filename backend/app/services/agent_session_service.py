from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timezone
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.context import ContextManager
from app.agent.event_recorder import EventRecorder
from app.agent.memory import default_memory_state
from app.agent.repository_provider import GitHubRepositoryProvider, GitLabRepositoryProvider
from app.agent.run_service import RunService
from app.agent.snapshot_service import SnapshotService
from app.db.models import (
    AgentArtifact,
    AgentMessage,
    AgentRun,
    AgentRunEvent,
    AgentSession,
    Project,
    RepositorySnapshot,
    User,
)
from app.db.session import get_db
from app.llm.client_factory import build_llm_client
from app.llm.provider import LLMConfig, load_llm_config
from app.schemas.agent import (
    AgentMessageCreateRequest,
    AgentMessageResponse,
    AgentSessionCreateRequest,
    AgentSessionResponse,
)


class AgentSessionService:
    DEFAULT_IDLE_POLL_LIMIT = 40
    ACTIVE_RUN_IDLE_POLL_LIMIT = 600

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def list_sessions(self, project_id: int) -> list[AgentSessionResponse]:
        self._get_project_or_404(project_id)
        sessions = self.session.scalars(
            select(AgentSession)
            .where(AgentSession.project_id == project_id)
            .order_by(AgentSession.updated_at.desc(), AgentSession.id.desc())
        ).all()
        return [self._to_session_response(item) for item in sessions]

    async def create_session(
        self,
        current_user: User,
        project_id: int,
        payload: AgentSessionCreateRequest,
    ) -> AgentSessionResponse:
        project = self._get_project_or_404(project_id)
        llm_config = self._load_llm_config()
        agent_session = AgentSession(
            project_id=project.id,
            created_by=current_user.id,
            title=payload.title,
            branch=payload.branch,
            status="active",
            provider=llm_config.provider,
            model=llm_config.model,
            memory_state=default_memory_state(),
            settings={},
        )
        self.session.add(agent_session)
        self.session.commit()
        self.session.refresh(agent_session)
        return self._to_session_response(agent_session)

    async def create_message(
        self,
        current_user: User,
        project_id: int,
        session_id: int,
        payload: AgentMessageCreateRequest,
    ) -> AgentMessageResponse:
        del current_user
        project = self._get_project_or_404(project_id)
        agent_session = self._get_session_for_update_or_404(
            project_id=project_id,
            session_id=session_id,
        )
        llm_config = self._load_llm_config()
        provider = self._build_repository_provider(project)
        model_client = self._build_model_client(llm_config)
        message = AgentMessage(
            session_id=agent_session.id,
            role="user",
            content=payload.content,
            content_format="markdown",
            status="completed",
            sequence=self._next_message_sequence(agent_session.id),
            metadata_payload={},
        )
        agent_session.last_message_at = datetime.now(timezone.utc)
        self.session.add(message)
        self.session.flush()

        run = AgentRun(
            session_id=agent_session.id,
            project_id=project.id,
            user_message_id=message.id,
            status="running",
            branch=agent_session.branch,
            prompt_metadata={},
            completion_metadata={},
            report_payload={},
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()
        message.run_id = run.id
        self.session.commit()

        self.session.refresh(message)
        self.session.refresh(run)
        self.session.refresh(agent_session)

        run_result = self._execute_run(
            project=project,
            agent_session=agent_session,
            user_message=message,
            llm_config=llm_config,
            provider=provider,
            model_client=model_client,
            run=run,
        )
        agent_session = self._get_session_for_update_or_404(
            project_id=project_id,
            session_id=session_id,
        )
        self._persist_run_result(
            project=project,
            agent_session=agent_session,
            user_message=message,
            run_result=run_result,
            run=run,
        )
        self.session.commit()
        self.session.refresh(message)
        return self._to_message_response(message)

    def stream_events(
        self,
        project_id: int,
        session_id: int,
        *,
        after_message_id: int = 0,
        after_event_id: int = 0,
    ) -> Iterator[str]:
        agent_session = self._get_session_or_404(project_id=project_id, session_id=session_id)
        last_message_id = max(0, int(after_message_id))
        last_event_id = max(0, int(after_event_id))
        idle_polls = 0
        terminal_seen = False
        active_run_seen = False

        while True:
            self.session.expire_all()
            agent_session = self._get_session_or_404(project_id=project_id, session_id=session_id)
            running_now = self._has_running_run(agent_session.id)
            active_run_seen = active_run_seen or running_now
            envelopes = self._load_stream_envelopes(
                session_id=agent_session.id,
                last_message_id=last_message_id,
                last_event_id=last_event_id,
            )
            if not envelopes:
                if terminal_seen and not running_now:
                    break
                idle_polls += 1
                idle_limit = (
                    self.ACTIVE_RUN_IDLE_POLL_LIMIT
                    if active_run_seen or running_now
                    else self.DEFAULT_IDLE_POLL_LIMIT
                )
                if idle_polls >= idle_limit:
                    break
                time.sleep(0.1)
                continue

            idle_polls = 0
            for envelope in envelopes:
                if envelope["kind"] == "message":
                    payload = envelope["data"]
                    last_message_id = max(last_message_id, int(payload["id"]))
                    yield self._format_sse(event="message", data=payload)
                    continue

                payload = envelope["data"]
                event_name = str(envelope["event"])
                last_event_id = max(last_event_id, int(payload["id"]))
                if event_name == "run_started":
                    active_run_seen = True
                if event_name in {"final_answer", "run_failed"}:
                    terminal_seen = True
                yield self._format_sse(event=event_name, data=payload)

        yield self._format_sse(
            event="ready",
            data={"session_id": agent_session.id, "status": agent_session.status},
        )

    def _load_llm_config(self) -> LLMConfig:
        return load_llm_config(default_provider="openai")

    def _build_model_client(self, llm_config: LLMConfig) -> Any:
        return build_llm_client(llm_config)

    def _build_repository_provider(self, project: Project) -> Any:
        if project.platform_type == "github":
            return GitHubRepositoryProvider(project=project)
        if project.platform_type == "gitlab":
            return GitLabRepositoryProvider(project=project)
        raise ValueError(f"Unsupported repository platform: {project.platform_type}")

    def _execute_run(
        self,
        *,
        project: Project,
        agent_session: AgentSession,
        user_message: AgentMessage,
        llm_config: LLMConfig,
        provider: Any,
        model_client: Any,
        run: AgentRun,
    ) -> dict[str, Any]:
        service = RunService(
            model_client=model_client,
            llm_config=llm_config,
            context_manager=ContextManager(),
            snapshot_service=SnapshotService(provider=provider),
            memory_state=agent_session.memory_state,
            provider=provider,
            branch=agent_session.branch,
            project_id=project.id,
            platform_type=project.platform_type,
            default_branch=project.default_branch,
            event_recorder=EventRecorder(
                persist_event=lambda event: self._persist_live_run_event(
                    run=run,
                    session_id=agent_session.id,
                    event=event,
                )
            ),
        )
        history_text = self._build_session_history(
            session_id=agent_session.id,
            before_sequence=user_message.sequence,
        )
        return service.run(user_message=user_message.content, history=history_text)

    def _persist_run_result(
        self,
        *,
        project: Project,
        agent_session: AgentSession,
        user_message: AgentMessage,
        run_result: dict[str, Any],
        run: AgentRun,
    ) -> None:
        run.status = str(run_result.get("status") or "failed")
        run.stop_reason = str(run_result.get("stop_reason") or "") or None
        run.tool_steps = int(run_result.get("tool_steps") or 0)
        run.attempts = int(run_result.get("attempts") or 0)
        run.last_tool = str(run_result.get("last_tool") or "") or None
        run.branch = str(run_result.get("branch") or agent_session.branch or "")
        run.head_sha = str(run_result.get("head_sha") or "") or None
        run.workspace_fingerprint = str(run_result.get("workspace_fingerprint") or "") or None
        run.runtime_identity_hash = str(run_result.get("runtime_identity_hash") or "") or None
        run.prompt_metadata = dict(run_result.get("prompt_metadata") or {})
        run.completion_metadata = dict(run_result.get("completion_metadata") or {})
        run.report_payload = dict(run_result.get("report_payload") or {})
        run.started_at = self._event_time(run_result.get("events"), first=True)
        run.finished_at = self._event_time(run_result.get("events"), first=False)
        user_message.run_id = run.id

        assistant_content = str(run_result.get("final_answer") or "").strip() or "运行未返回最终答案。"
        assistant_message = AgentMessage(
            session_id=agent_session.id,
            run_id=run.id,
            role="assistant",
            content=assistant_content,
            content_format="markdown",
            status="completed" if run.status == "completed" else "failed",
            sequence=self._next_message_sequence(agent_session.id),
            metadata_payload={},
        )
        self.session.add(assistant_message)
        self.session.flush()
        run.assistant_message_id = assistant_message.id

        for artifact in run_result.get("artifacts", []):
            if not isinstance(artifact, dict):
                continue
            self.session.add(
                AgentArtifact(
                    run_id=run.id,
                    session_id=agent_session.id,
                    artifact_type=str(artifact.get("artifact_type") or "artifact"),
                    name=str(artifact.get("name") or "artifact"),
                    content=json.dumps(artifact.get("content"), ensure_ascii=False),
                    metadata_payload=dict(artifact.get("metadata") or {}),
                )
            )

        snapshot = run_result.get("snapshot")
        if snapshot is not None:
            existing_snapshot = self.session.scalar(
                select(RepositorySnapshot).where(
                    RepositorySnapshot.project_id == project.id,
                    RepositorySnapshot.branch == snapshot.branch,
                    RepositorySnapshot.head_sha == snapshot.head_sha,
                )
            )
            if existing_snapshot is None:
                self.session.add(
                    RepositorySnapshot(
                        project_id=project.id,
                        branch=snapshot.branch,
                        head_sha=snapshot.head_sha,
                        workspace_fingerprint=str(run_result.get("workspace_fingerprint") or ""),
                        snapshot_digest=snapshot.snapshot_digest,
                        file_tree_summary=snapshot.file_tree_summary,
                        project_docs_summary=snapshot.project_docs_summary,
                        recent_commits_summary=snapshot.recent_commits_summary,
                        metadata_payload={},
                    )
                )

        completion_metadata = dict(run_result.get("completion_metadata") or {})
        agent_session.last_head_sha = str(run_result.get("head_sha") or "") or None
        agent_session.last_workspace_fingerprint = str(run_result.get("workspace_fingerprint") or "") or None
        agent_session.last_runtime_identity_hash = str(run_result.get("runtime_identity_hash") or "") or None
        agent_session.memory_state = dict(run_result.get("memory_state") or agent_session.memory_state or {})
        agent_session.provider = str(completion_metadata.get("provider") or agent_session.provider or "")
        agent_session.model = str(completion_metadata.get("model") or agent_session.model or "")
        agent_session.last_message_at = datetime.now(UTC)

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.session.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在。",
            )
        return project

    def _get_session_or_404(self, *, project_id: int, session_id: int) -> AgentSession:
        self._get_project_or_404(project_id)
        agent_session = self.session.scalar(
            select(AgentSession).where(
                AgentSession.id == session_id,
                AgentSession.project_id == project_id,
            )
        )
        if agent_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在。",
            )
        return agent_session

    def _get_session_for_update_or_404(self, *, project_id: int, session_id: int) -> AgentSession:
        self._get_project_or_404(project_id)
        agent_session = self.session.scalar(
            select(AgentSession)
            .where(
                AgentSession.id == session_id,
                AgentSession.project_id == project_id,
            )
            .with_for_update()
        )
        if agent_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在。",
            )
        return agent_session

    def _next_message_sequence(self, session_id: int) -> int:
        current = self.session.scalar(
            select(func.max(AgentMessage.sequence)).where(AgentMessage.session_id == session_id)
        )
        return int(current or 0) + 1

    def _build_session_history(self, *, session_id: int, before_sequence: int) -> str:
        rows = self.session.scalars(
            select(AgentMessage)
            .where(
                AgentMessage.session_id == session_id,
                AgentMessage.sequence < before_sequence,
            )
            .order_by(AgentMessage.sequence.asc(), AgentMessage.id.asc())
        ).all()
        if not rows:
            return ""

        history_lines: list[str] = []
        for row in rows[-12:]:
            role = "User" if row.role == "user" else "Assistant"
            content = " ".join(str(row.content or "").split()).strip()
            if not content:
                continue
            history_lines.append(f"{role}: {content}")
        return "\n".join(history_lines)

    def _has_running_run(self, session_id: int) -> bool:
        running = self.session.scalar(
            select(AgentRun.id)
            .where(
                AgentRun.session_id == session_id,
                AgentRun.status == "running",
            )
            .limit(1)
        )
        return running is not None

    @staticmethod
    def _to_session_response(agent_session: AgentSession) -> AgentSessionResponse:
        return AgentSessionResponse(
            id=agent_session.id,
            project_id=agent_session.project_id,
            title=agent_session.title,
            status=agent_session.status,
            branch=agent_session.branch,
            provider=agent_session.provider,
            model=agent_session.model,
            created_by=agent_session.created_by,
            created_at=agent_session.created_at,
            updated_at=agent_session.updated_at,
            last_message_at=agent_session.last_message_at,
        )

    @staticmethod
    def _to_message_response(message: AgentMessage) -> AgentMessageResponse:
        return AgentMessageResponse(
            id=message.id,
            session_id=message.session_id,
            run_id=message.run_id,
            role=message.role,
            content=message.content,
            status=message.status,
            sequence=message.sequence,
            content_format=message.content_format,
            created_at=message.created_at,
        )

    @staticmethod
    def _format_sse(*, event: str, data: dict[str, object]) -> str:
        encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {encoded}\n\n"

    @staticmethod
    def _event_time(events: Any, *, first: bool) -> datetime | None:
        if not isinstance(events, list) or not events:
            return None
        iterable = events if first else reversed(events)
        for event in iterable:
            if not isinstance(event, dict):
                continue
            created_at = event.get("created_at")
            if isinstance(created_at, datetime):
                return created_at
        return None

    def _persist_live_run_event(
        self,
        *,
        run: AgentRun,
        session_id: int,
        event: dict[str, Any],
    ) -> None:
        created_at = event.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = datetime.now(UTC)
        event_type = str(event.get("event_type") or "unknown")
        payload = dict(event.get("payload") or {})
        self.session.add(
            AgentRunEvent(
                run_id=run.id,
                session_id=session_id,
                event_type=event_type,
                sequence=int(event.get("sequence") or 0),
                payload=payload,
                created_at=created_at,
            )
        )
        if event_type == "tool_called":
            run.last_tool = str(payload.get("tool_name") or "") or None
        if event_type == "run_started":
            run.started_at = created_at
        if event_type in {"final_answer", "run_failed"}:
            run.finished_at = created_at
        self.session.commit()
        self.session.refresh(run)

    def _load_stream_envelopes(
        self,
        *,
        session_id: int,
        last_message_id: int,
        last_event_id: int,
    ) -> list[dict[str, Any]]:
        message_rows = self.session.scalars(
            select(AgentMessage)
            .where(
                AgentMessage.session_id == session_id,
                AgentMessage.id > last_message_id,
            )
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
        ).all()
        event_rows = self.session.scalars(
            select(AgentRunEvent)
            .where(
                AgentRunEvent.session_id == session_id,
                AgentRunEvent.id > last_event_id,
            )
            .order_by(AgentRunEvent.created_at.asc(), AgentRunEvent.id.asc())
        ).all()
        envelopes: list[dict[str, Any]] = []
        for message in message_rows:
            envelopes.append(
                {
                    "kind": "message",
                    "event": "message",
                    "sort_at": message.created_at,
                    "sort_id": int(message.id),
                    "data": {
                        "id": message.id,
                        "session_id": message.session_id,
                        "role": message.role,
                        "content": message.content,
                        "status": message.status,
                        "sequence": message.sequence,
                        "created_at": message.created_at.isoformat(),
                    },
                }
            )
        for event in event_rows:
            envelopes.append(
                {
                    "kind": "run_event",
                    "event": event.event_type,
                    "sort_at": event.created_at,
                    "sort_id": int(event.id),
                    "data": {
                        "id": event.id,
                        "run_id": event.run_id,
                        "session_id": event.session_id,
                        "sequence": event.sequence,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat(),
                    },
                }
            )
        envelopes.sort(
            key=lambda item: (
                item["sort_at"],
                0 if item["kind"] == "message" else 1,
                item["sort_id"],
            )
        )
        return envelopes
