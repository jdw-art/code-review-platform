from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.context import ContextManager
from app.agent.event_recorder import AgentEventRecorder
from app.agent.memory import default_memory_state
from app.agent.tool_gateway import AgentToolGateway
from app.agent.tools import READ_ONLY_TOOL_SPECS
from app.agent.workspace import WorkspaceContext
from app.db.models import AgentMessage, AgentRun, AgentSession, Project, RepositorySnapshot
from app.services.agent_session_service import AgentSessionService


class AgentModelClient(Protocol):
    def complete(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        pass


class AgentRunService:
    def __init__(
        self,
        *,
        session: Session,
        model_client: AgentModelClient,
        tool_gateway: AgentToolGateway,
        event_recorder: AgentEventRecorder,
        session_service: AgentSessionService | None = None,
        max_steps: int = 6,
    ) -> None:
        self.session = session
        self.model_client = model_client
        self.tool_gateway = tool_gateway
        self.event_recorder = event_recorder
        self.session_service = session_service or AgentSessionService(session)
        self.max_steps = int(max_steps)

    def run(self, run_id: int) -> AgentRun:
        run = self._require_run(run_id)
        agent_session = self._require_session(run.session_id)
        assistant_message = self._require_message(run.assistant_message_id)
        user_message = self._require_message(run.user_message_id)
        project = self._require_project(run.project_id)
        snapshot = self._require_snapshot(run.snapshot_id or agent_session.snapshot_id)

        history = self._load_history(
            session_id=agent_session.id,
            before_sequence=user_message.sequence,
        )
        memory_state = self._normalize_memory_state(agent_session.memory_state)
        workspace = self._build_workspace(project=project, snapshot=snapshot, settings=agent_session.settings)
        prompt, prompt_metadata = self._build_prompt(
            workspace=workspace,
            snapshot_id=snapshot.id,
            memory_state=memory_state,
            history=history,
            user_message=user_message.content,
            attempt=1,
        )

        self.event_recorder.record(
            run_id=run.id,
            session_id=agent_session.id,
            event_type="run_started",
            payload={
                "run_id": run.id,
                "assistant_message_id": assistant_message.id,
                "snapshot_id": snapshot.id,
                "workspace_fingerprint": workspace.fingerprint,
            },
        )

        attempts = 0
        tool_steps = 0
        last_tool = ""

        while True:
            if tool_steps >= self.max_steps and attempts > 0:
                return self.session_service.stop_run(
                    session=agent_session,
                    run=run,
                    assistant_message=assistant_message,
                    status="stopped",
                    stop_reason="step_limit_reached",
                    prompt_metadata=prompt_metadata,
                    completion_metadata={
                        "attempts": attempts,
                        "tool_steps": tool_steps,
                        "last_tool": last_tool,
                    },
                    memory_state=memory_state,
                )

            run.prompt_metadata = dict(prompt_metadata)
            run.workspace_fingerprint = workspace.fingerprint
            run.snapshot_id = snapshot.id
            self.session.flush()

            try:
                response_text = self.model_client.complete(
                    prompt=prompt,
                    metadata=prompt_metadata,
                )
            except Exception as exc:
                self.event_recorder.record(
                    run_id=run.id,
                    session_id=agent_session.id,
                    event_type="error",
                    payload={"message": str(exc), "stop_reason": "model_error"},
                )
                return self.session_service.stop_run(
                    session=agent_session,
                    run=run,
                    assistant_message=assistant_message,
                    status="failed",
                    stop_reason="model_error",
                    prompt_metadata=prompt_metadata,
                    completion_metadata={
                        "attempts": attempts,
                        "tool_steps": tool_steps,
                        "last_tool": last_tool,
                    },
                    memory_state=memory_state,
                )

            attempts += 1
            run.attempts = attempts
            tool_call = self._parse_tool_call(response_text)

            if tool_call is None:
                self.event_recorder.record(
                    run_id=run.id,
                    session_id=agent_session.id,
                    event_type="assistant_delta",
                    payload={"delta": response_text},
                )
                self.event_recorder.record(
                    run_id=run.id,
                    session_id=agent_session.id,
                    event_type="assistant_message",
                    payload={
                        "message_id": assistant_message.id,
                        "content": response_text,
                    },
                )
                self.event_recorder.record(
                    run_id=run.id,
                    session_id=agent_session.id,
                    event_type="final",
                    payload={
                        "final_answer": response_text,
                        "stop_reason": "final_answer_returned",
                    },
                )
                return self.session_service.complete_run(
                    session=agent_session,
                    run=run,
                    assistant_message=assistant_message,
                    final_answer=response_text,
                    stop_reason="final_answer_returned",
                    prompt_metadata=prompt_metadata,
                    completion_metadata={
                        "attempts": attempts,
                        "tool_steps": tool_steps,
                        "last_tool": last_tool,
                    },
                    memory_state=memory_state,
                )

            name = tool_call["name"]
            args = tool_call["args"]
            self.event_recorder.record(
                run_id=run.id,
                session_id=agent_session.id,
                event_type="tool_start",
                payload={"name": name, "args": args},
            )
            result = self.tool_gateway.execute(
                name,
                args,
                snapshot_id=snapshot.id,
                history=history,
            )
            tool_steps += 1
            last_tool = name
            run.tool_steps = tool_steps
            run.last_tool = last_tool
            self.event_recorder.record(
                run_id=run.id,
                session_id=agent_session.id,
                event_type="tool_result",
                payload={
                    "name": result.name,
                    "args": result.args,
                    "output": result.output,
                    "status": result.status,
                    "cached": result.cached,
                    "error_code": result.error_code,
                },
            )

            history.append(
                {
                    "role": "tool",
                    "name": result.name,
                    "args": result.args,
                    "content": result.output,
                }
            )
            memory_state = self._apply_tool_result(memory_state, result.name, result.args, result.output)

            if result.status == "error":
                self.event_recorder.record(
                    run_id=run.id,
                    session_id=agent_session.id,
                    event_type="error",
                    payload={
                        "message": result.output,
                        "stop_reason": "tool_error",
                        "tool": result.name,
                    },
                )
                return self.session_service.stop_run(
                    session=agent_session,
                    run=run,
                    assistant_message=assistant_message,
                    status="failed",
                    stop_reason="tool_error",
                    prompt_metadata=prompt_metadata,
                    completion_metadata={
                        "attempts": attempts,
                        "tool_steps": tool_steps,
                        "last_tool": last_tool,
                    },
                    memory_state=memory_state,
                    assistant_content=result.output,
                )

            prompt, prompt_metadata = self._build_prompt(
                workspace=workspace,
                snapshot_id=snapshot.id,
                memory_state=memory_state,
                history=history,
                user_message=user_message.content,
                attempt=attempts + 1,
            )

    def _build_prompt(
        self,
        *,
        workspace: WorkspaceContext,
        snapshot_id: int,
        memory_state: dict[str, Any],
        history: list[dict[str, Any]],
        user_message: str,
        attempt: int,
    ) -> tuple[str, dict[str, Any]]:
        manager = ContextManager(
            workspace_text=self._prefix_text(workspace),
            memory_state=memory_state,
            history=history,
        )
        prompt, metadata = manager.build(user_message)
        metadata.update(
            {
                "attempt": attempt,
                "workspace_fingerprint": workspace.fingerprint,
                "snapshot_id": snapshot_id,
                "prompt": prompt,
            }
        )
        return prompt, metadata

    def _build_workspace(
        self,
        *,
        project: Project,
        snapshot: RepositorySnapshot,
        settings: dict[str, Any],
    ) -> WorkspaceContext:
        settings_hash = hashlib.sha256(
            json.dumps(settings or {}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        fingerprint = WorkspaceContext.build_fingerprint(
            {
                "project_id": project.id,
                "project_name": project.name,
                "platform_type": project.platform_type,
                "repo_url": project.repo_url,
                "ref": snapshot.ref,
                "head_sha": snapshot.head_sha,
                "snapshot_id": snapshot.id,
                "tool_signature": self._tool_signature(),
                "settings_hash": settings_hash,
            }
        )
        return WorkspaceContext(
            project_id=project.id,
            project_name=project.name,
            platform_type=project.platform_type,
            repo_url=project.repo_url,
            ref=snapshot.ref,
            head_sha=snapshot.head_sha,
            fingerprint=fingerprint,
            overview=snapshot.overview,
            recent_commits=snapshot.recent_commits,
        )

    def _load_history(self, *, session_id: int, before_sequence: int) -> list[dict[str, Any]]:
        messages = self.session.scalars(
            select(AgentMessage)
            .where(
                AgentMessage.session_id == session_id,
                AgentMessage.sequence < before_sequence,
            )
            .order_by(AgentMessage.sequence.asc())
        ).all()
        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

    @staticmethod
    def _normalize_memory_state(memory_state: dict[str, Any] | None) -> dict[str, Any]:
        base = default_memory_state()
        state = dict(memory_state or {})
        base["working"].update(state.get("working", {}))
        for key in ("episodic_notes", "notes", "files"):
            if isinstance(state.get(key), list):
                base[key] = list(state[key])
        for key in ("file_summaries",):
            if isinstance(state.get(key), dict):
                base[key] = dict(state[key])
        if isinstance(state.get("task"), str):
            base["task"] = state["task"]
        if isinstance(state.get("next_note_index"), int):
            base["next_note_index"] = state["next_note_index"]
        return base

    @staticmethod
    def _apply_tool_result(
        memory_state: dict[str, Any],
        name: str,
        args: dict[str, Any],
        output: str,
    ) -> dict[str, Any]:
        working = memory_state.setdefault("working", {})
        recent_files = list(working.get("recent_files", []))
        if name == "read_file":
            path = str(args.get("path", "")).strip()
            if path:
                recent_files = [item for item in recent_files if item != path]
                recent_files.append(path)
                working["recent_files"] = recent_files[-10:]
                memory_state.setdefault("file_summaries", {})[path] = output[:240]
        working["task_summary"] = str(working.get("task_summary", "")) or "Repository Q&A"
        return memory_state

    @staticmethod
    def _parse_tool_call(response_text: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        tool = payload.get("tool")
        if not isinstance(tool, dict):
            return None
        name = tool.get("name")
        args = tool.get("args", {})
        if not isinstance(name, str) or not isinstance(args, dict):
            return None
        return {"name": name, "args": args}

    @staticmethod
    def _prefix_text(workspace: WorkspaceContext) -> str:
        tool_lines = "\n".join(
            f"- {spec.name}({', '.join(f'{key}={value}' for key, value in spec.schema.items())})"
            f": {spec.description}"
            for spec in READ_ONLY_TOOL_SPECS.values()
        )
        return (
            "Instructions:\n"
            "- You are a repository understanding assistant for the current project.\n"
            "- Use read-only tools when the answer requires repository evidence.\n"
            "- If you need a tool, respond with a JSON object matching "
            '{"tool": {"name": "...", "args": {...}}}.\n'
            "- Otherwise return the final answer directly in markdown.\n\n"
            f"{workspace.text()}\n\n"
            "Tools:\n"
            f"{tool_lines}\n\n"
            "Output rules:\n"
            "- Prefer concrete file paths and concise explanations.\n"
            "- Do not invent repository contents you have not read."
        )

    @staticmethod
    def _tool_signature() -> str:
        payload = {
            name: spec.schema
            for name, spec in sorted(READ_ONLY_TOOL_SPECS.items())
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _require_run(self, run_id: int) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if run is None:
            raise ValueError(f"run {run_id} not found")
        return run

    def _require_session(self, session_id: int) -> AgentSession:
        agent_session = self.session.get(AgentSession, session_id)
        if agent_session is None:
            raise ValueError(f"session {session_id} not found")
        return agent_session

    def _require_project(self, project_id: int) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise ValueError(f"project {project_id} not found")
        return project

    def _require_snapshot(self, snapshot_id: int | None) -> RepositorySnapshot:
        if snapshot_id is None:
            raise ValueError("snapshot not found")
        snapshot = self.session.get(RepositorySnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id} not found")
        return snapshot

    def _require_message(self, message_id: int | None) -> AgentMessage:
        if message_id is None:
            raise ValueError("message not found")
        message = self.session.get(AgentMessage, message_id)
        if message is None:
            raise ValueError(f"message {message_id} not found")
        return message
