from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.memory import default_memory_state
from app.agent.tools import READ_ONLY_TOOL_SPECS
from app.agent.workspace import WorkspaceContext
from app.db.models import AgentMessage, AgentRun, AgentSession, Project, RepositorySnapshot


class AgentSessionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(
        self,
        *,
        project: Project,
        title: str,
        created_by: int | None,
        snapshot: RepositorySnapshot | None = None,
        provider: str | None = None,
        model: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> AgentSession:
        settings_payload = dict(settings or {})
        memory_state = default_memory_state()
        workspace_fingerprint = self._build_workspace_fingerprint(
            project=project,
            snapshot=snapshot,
            settings=settings_payload,
        )
        agent_session = AgentSession(
            project_id=project.id,
            created_by=created_by,
            title=title,
            status="active",
            provider=provider,
            model=model,
            workspace_fingerprint=workspace_fingerprint,
            snapshot_id=snapshot.id if snapshot is not None else None,
            memory_state=memory_state,
            settings=settings_payload,
        )
        self.session.add(agent_session)
        self.session.commit()
        self.session.refresh(agent_session)
        return agent_session

    def list_sessions(self, *, project_id: int) -> list[AgentSession]:
        return list(
            self.session.scalars(
                select(AgentSession)
                .where(AgentSession.project_id == project_id)
                .order_by(AgentSession.updated_at.desc(), AgentSession.id.desc())
            ).all()
        )

    def get_session(self, *, session_id: int) -> AgentSession | None:
        return self.session.get(AgentSession, session_id)

    def list_messages(self, *, session_id: int) -> list[AgentMessage]:
        return list(
            self.session.scalars(
                select(AgentMessage)
                .where(AgentMessage.session_id == session_id)
                .order_by(AgentMessage.sequence.asc())
            ).all()
        )

    def get_run(self, *, run_id: int) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def create_message_pair_and_run(
        self,
        *,
        session: AgentSession,
        content: str,
    ) -> tuple[AgentMessage, AgentMessage, AgentRun]:
        next_sequence = self._next_message_sequence(session.id)
        user_message = AgentMessage(
            session_id=session.id,
            role="user",
            content=content,
            content_format="markdown",
            status="completed",
            sequence=next_sequence,
            metadata_json={},
        )
        assistant_message = AgentMessage(
            session_id=session.id,
            role="assistant",
            content="",
            content_format="markdown",
            status="streaming",
            sequence=next_sequence + 1,
            metadata_json={},
        )
        self.session.add_all([user_message, assistant_message])
        self.session.flush()

        run = AgentRun(
            session_id=session.id,
            project_id=session.project_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            status="running",
            stop_reason="",
            tool_steps=0,
            attempts=0,
            last_tool="",
            final_answer=None,
            prompt_metadata={},
            completion_metadata={},
            workspace_fingerprint=session.workspace_fingerprint,
            snapshot_id=session.snapshot_id,
        )
        self.session.add(run)
        self.session.flush()

        assistant_message.run_id = run.id
        session.last_message_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(user_message)
        self.session.refresh(assistant_message)
        self.session.refresh(run)
        return user_message, assistant_message, run

    def complete_run(
        self,
        *,
        session: AgentSession,
        run: AgentRun,
        assistant_message: AgentMessage,
        final_answer: str,
        stop_reason: str,
        prompt_metadata: dict[str, Any],
        completion_metadata: dict[str, Any],
        memory_state: dict[str, Any],
    ) -> AgentRun:
        assistant_message.content = final_answer
        assistant_message.status = "completed"
        run.status = "completed"
        run.stop_reason = stop_reason
        run.final_answer = final_answer
        run.prompt_metadata = dict(prompt_metadata)
        run.completion_metadata = dict(completion_metadata)
        session.memory_state = dict(memory_state)
        session.last_message_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(run)
        return run

    def stop_run(
        self,
        *,
        session: AgentSession,
        run: AgentRun,
        assistant_message: AgentMessage,
        status: str,
        stop_reason: str,
        prompt_metadata: dict[str, Any],
        completion_metadata: dict[str, Any],
        memory_state: dict[str, Any],
        assistant_content: str = "",
    ) -> AgentRun:
        assistant_message.content = assistant_content
        assistant_message.status = status
        run.status = status
        run.stop_reason = stop_reason
        run.prompt_metadata = dict(prompt_metadata)
        run.completion_metadata = dict(completion_metadata)
        session.memory_state = dict(memory_state)
        session.last_message_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(run)
        return run

    def _next_message_sequence(self, session_id: int) -> int:
        max_sequence = self.session.scalar(
            select(func.max(AgentMessage.sequence)).where(AgentMessage.session_id == session_id)
        )
        return 1 if max_sequence is None else int(max_sequence) + 1

    def _build_workspace_fingerprint(
        self,
        *,
        project: Project,
        snapshot: RepositorySnapshot | None,
        settings: dict[str, Any],
    ) -> str:
        if snapshot is None:
            return ""
        return WorkspaceContext.build_fingerprint(
            {
                "project_id": project.id,
                "project_name": project.name,
                "platform_type": project.platform_type,
                "repo_url": project.repo_url,
                "ref": snapshot.ref,
                "head_sha": snapshot.head_sha,
                "snapshot_id": snapshot.id,
                "tool_signature": self._tool_signature(),
                "settings_hash": self._settings_hash(settings),
            }
        )

    @staticmethod
    def _settings_hash(settings: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(settings or {}, sort_keys=True).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _tool_signature() -> str:
        payload = {
            name: spec.schema
            for name, spec in sorted(READ_ONLY_TOOL_SPECS.items())
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
