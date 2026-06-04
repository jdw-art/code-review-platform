from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Protocol

from app.agent.context import ContextManager
from app.agent.event_recorder import EventRecorder
from app.agent.memory import (
    default_memory_state,
    invalidate_stale_file_summaries,
    normalize_memory_state,
)
from app.agent.protocol import parse_agent_response
from app.agent.snapshot_service import SnapshotService
from app.agent.tool_gateway import ToolGateway
from app.agent.workspace import build_runtime_identity_hash, build_workspace_fingerprint
from app.llm.client_factory import build_llm_client
from app.llm.provider import LLMConfig, load_llm_config


DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_REPORT_NOTE = "运行未返回最终答案。"


class SupportsCompletions(Protocol):
    def completions(self, *, messages: list[dict[str, str]]) -> str: ...


class FakeModelClient:
    def __init__(self, *, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.calls: list[list[dict[str, str]]] = []

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        self.calls.append(deepcopy(messages))
        if not self.outputs:
            raise RuntimeError("FakeModelClient has no more prepared outputs")
        return str(self.outputs.pop(0))


class RunService:
    def __init__(
        self,
        *,
        model_client: SupportsCompletions | Any | None,
        context_manager: ContextManager,
        snapshot_service: SnapshotService,
        memory_state: dict[str, Any] | None,
        provider: Any,
        branch: str,
        project_id: int | str,
        platform_type: str,
        default_branch: str,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        secret_values: list[str] | None = None,
        event_recorder: EventRecorder | None = None,
        llm_config: LLMConfig | None = None,
    ) -> None:
        self.model_client = model_client
        self.context_manager = context_manager
        self.snapshot_service = snapshot_service
        self.memory_state = normalize_memory_state(memory_state or default_memory_state())
        self.provider = provider
        self.branch = str(branch)
        self.project_id = project_id
        self.platform_type = str(platform_type)
        self.default_branch = str(default_branch)
        self.max_attempts = max(1, int(max_attempts))
        self.secret_values = list(secret_values or [])
        self.event_recorder = event_recorder or EventRecorder()
        self.llm_config = llm_config

    def run(self, *, user_message: str, history: str = "") -> dict[str, Any]:
        initial_memory_state = normalize_memory_state(self.memory_state)
        snapshot = self.snapshot_service.build(
            project_id=self.project_id,
            platform_type=self.platform_type,
            default_branch=self.default_branch,
            branch=self.branch,
        )
        llm_config, model_client = self._resolve_model_client()
        tool_gateway = ToolGateway(
            provider=self.provider,
            branch=self.branch,
            ref=snapshot.head_sha,
            secret_values=self.secret_values,
            project_docs_summary=snapshot.project_docs_summary,
        )
        workspace_fingerprint = build_workspace_fingerprint(snapshot)
        runtime_identity_hash = build_runtime_identity_hash(
            {
                "workspace_fingerprint": workspace_fingerprint,
                "tool_signature": tool_gateway.tool_signature(),
                "provider": llm_config.provider,
                "model": llm_config.model,
                "max_steps": self.max_attempts,
                "read_only": True,
            }
        )
        memory_state, invalidated = invalidate_stale_file_summaries(
            self.memory_state,
            snapshot.file_tree_summary.get("files", {}),
        )
        self.event_recorder.record(
            "run_started",
            {
                "branch": self.branch,
                "head_sha": snapshot.head_sha,
                "provider": llm_config.provider,
                "model": llm_config.model,
                "workspace_fingerprint": workspace_fingerprint,
                "runtime_identity_hash": runtime_identity_hash,
                "snapshot_digest": snapshot.snapshot_digest,
            },
        )
        self.event_recorder.record(
            "snapshot_resolved",
            {
                "branch": snapshot.branch,
                "head_sha": snapshot.head_sha,
                "doc_count": len(snapshot.project_docs_summary),
                "recent_commit_count": len(snapshot.recent_commits_summary),
            },
        )
        if invalidated:
            self.event_recorder.record("memory_invalidated", {"paths": invalidated})

        tool_steps = 0
        attempts = 0
        history_text = str(history).strip()
        prompt_metadata: dict[str, Any] = {}
        last_tool: str | None = None

        while attempts < self.max_attempts:
            attempts += 1
            prompt, prompt_metadata = self.context_manager.build(
                prefix=self._build_prefix(snapshot=snapshot, tool_gateway=tool_gateway),
                memory_state=memory_state,
                history=history_text,
                current_request=str(user_message),
            )
            self.event_recorder.record(
                "prompt_built",
                {
                    "attempt": attempts,
                    "prompt_chars": prompt_metadata.get("prompt_chars"),
                    "prompt_budget_chars": prompt_metadata.get("prompt_budget_chars"),
                },
            )
            raw_response = self._complete(
                messages=[{"role": "user", "content": prompt}],
                model_client=model_client,
            )
            kind, payload = parse_agent_response(raw_response)

            if kind == "tool":
                tool_name = str(payload["name"])
                tool_args = dict(payload.get("args") or {})
                last_tool = tool_name
                self.event_recorder.record(
                    "tool_called",
                    {
                        "attempt": attempts,
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                    },
                )
                tool_output = tool_gateway.run(tool_name, tool_args)
                tool_steps += 1
                self.event_recorder.record(
                    "tool_result",
                    {
                        "attempt": attempts,
                        "tool_name": tool_name,
                        "tool_result": tool_output,
                    },
                )
                memory_state = self._update_memory_from_tool(
                    memory_state=memory_state,
                    snapshot=snapshot,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_output=tool_output,
                )
                history_text = self._append_history(
                    history_text,
                    f"Assistant tool call: {raw_response}\nTool result:\n{tool_output}",
                )
                continue

            if kind == "final":
                final_answer = str(payload)
                final_retry_notice = self._validate_final_answer(
                    final_answer=final_answer,
                    user_message=user_message,
                    history_text=history_text,
                    tool_steps=tool_steps,
                )
                if final_retry_notice is not None:
                    self.event_recorder.record(
                        "model_retry",
                        {
                            "attempt": attempts,
                            "notice": final_retry_notice,
                        },
                    )
                    history_text = self._append_history(
                        history_text,
                        f"Assistant premature final answer: {raw_response}\nRuntime notice: {final_retry_notice}",
                    )
                    continue
                memory_state = self._update_memory_from_final(
                    memory_state=memory_state,
                    user_message=user_message,
                    final_answer=final_answer,
                )
                self.event_recorder.record(
                    "assistant_delta",
                    {
                        "attempt": attempts,
                        "delta": final_answer,
                    },
                )
                self.event_recorder.record(
                    "final_answer",
                    {
                        "attempt": attempts,
                        "final_answer": final_answer,
                    },
                )
                report_payload = {
                    "status": "completed",
                    "attempts": attempts,
                    "tool_steps": tool_steps,
                    "final_answer": final_answer,
                }
                return {
                    "status": "completed",
                    "stop_reason": "final_answer",
                    "final_answer": final_answer,
                    "tool_steps": tool_steps,
                    "attempts": attempts,
                    "last_tool": last_tool,
                    "events": self.event_recorder.export(),
                    "branch": self.branch,
                    "head_sha": snapshot.head_sha,
                    "snapshot_digest": snapshot.snapshot_digest,
                    "workspace_fingerprint": workspace_fingerprint,
                    "runtime_identity_hash": runtime_identity_hash,
                    "prompt_metadata": prompt_metadata,
                    "completion_metadata": self._completion_metadata(
                        llm_config=llm_config,
                        attempts=attempts,
                        tool_steps=tool_steps,
                    ),
                    "memory_state": memory_state,
                    "snapshot": snapshot,
                    "report_payload": report_payload,
                    "artifacts": self._build_artifacts(
                        prompt_metadata=prompt_metadata,
                        initial_memory_state=initial_memory_state,
                        memory_state=memory_state,
                        report_payload=report_payload,
                        snapshot=snapshot,
                    ),
                }

            retry_notice = str(payload)
            self.event_recorder.record(
                "model_retry",
                {
                    "attempt": attempts,
                    "notice": retry_notice,
                    "raw_response_preview": self._clip_text(raw_response, limit=1200),
                },
            )
            history_text = self._append_history(
                history_text,
                f"Assistant invalid response: {raw_response}\nRuntime notice: {retry_notice}",
            )

        self.event_recorder.record(
            "run_failed",
            {
                "attempts": attempts,
                "reason": "max_attempts_exceeded",
            },
        )
        report_payload = {
            "status": "failed",
            "attempts": attempts,
            "tool_steps": tool_steps,
            "final_answer": "",
        }
        return {
            "status": "failed",
            "stop_reason": "max_attempts_exceeded",
            "final_answer": "",
            "tool_steps": tool_steps,
            "attempts": attempts,
            "last_tool": last_tool,
            "events": self.event_recorder.export(),
            "branch": self.branch,
            "head_sha": snapshot.head_sha,
            "snapshot_digest": snapshot.snapshot_digest,
            "workspace_fingerprint": workspace_fingerprint,
            "runtime_identity_hash": runtime_identity_hash,
            "prompt_metadata": prompt_metadata,
            "completion_metadata": self._completion_metadata(
                llm_config=llm_config,
                attempts=attempts,
                tool_steps=tool_steps,
            ),
            "memory_state": memory_state,
            "snapshot": snapshot,
            "report_payload": report_payload,
            "artifacts": self._build_artifacts(
                prompt_metadata=prompt_metadata,
                initial_memory_state=initial_memory_state,
                memory_state=memory_state,
                report_payload=report_payload,
                snapshot=snapshot,
            ),
        }

    def _resolve_model_client(self) -> tuple[LLMConfig, Any]:
        if self.model_client is not None:
            return (
                self.llm_config
                or LLMConfig(
                    provider="test",
                    api_key=None,
                    api_base_url=None,
                    model="fake-model",
                    required_env=(),
                ),
                self.model_client,
            )
        llm_config = self.llm_config or load_llm_config(default_provider="openai")
        return llm_config, build_llm_client(llm_config)

    @staticmethod
    def _complete(*, messages: list[dict[str, str]], model_client: Any) -> str:
        if hasattr(model_client, "completions"):
            return str(model_client.completions(messages=messages))
        if hasattr(model_client, "complete"):
            return str(model_client.complete(messages=messages))
        raise TypeError("model_client must provide completions(messages=...) or complete(messages=...)")

    def _build_prefix(self, *, snapshot: Any, tool_gateway: ToolGateway) -> str:
        rules = [
            "Rules:",
            "- Use tools instead of guessing about the repository.",
            "- Return exactly one <tool>...</tool> or one <final>...</final>.",
            '- Tool calls must look like: <tool>{"name":"tool_name","args":{...}}</tool>',
            "- Final answers must look like: <final>your answer</final>",
            "- Do not write any natural-language text outside the top-level tag.",
            "- Never invent tool results.",
            "- Keep answers concise and concrete.",
            "- Do not repeat the same tool call with the same arguments if it did not help.",
            "- When you already have enough evidence to answer the user, stop calling tools and return <final> immediately.",
            "- If the user asks where an entrypoint is, prefer one quick discovery tool call plus one focused read, then answer.",
            "- For follow-up questions that mention the previous round, first reuse evidence from History and Memory.recent_files before exploring the wider repository.",
            "- Prefer a local import-chain expansion: from the last confirmed file, read the nearest imported or adjacent module instead of broad repo-wide search.",
            "- Avoid broad search_code on path='.' unless recent files, nearby modules, and project docs are insufficient.",
            "- read_file supports at most 200 lines per call; prefer focused windows such as 1-120 or 1-160.",
            "- If the current evidence already shows that a file is only an entrypoint or initializer, you may answer what it does, what it does not do, and which next file is the likely auth/router location.",
            "- After two or three focused tool calls around one chain, return <final> with known facts, uncertainties, and recommended next files instead of continuing to hunt globally.",
        ]
        examples = [
            "Valid response examples:",
            '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
            '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":80}}</tool>',
            "<final>后端入口在 api.py，它先 load_dotenv，再导入并初始化 biz.api 中的 API 应用。</final>",
        ]
        lines = [
            "You are Repo Agent. Use the repository snapshot and the available read-only tools.",
            f"Project ID: {snapshot.project_id}",
            f"Platform: {snapshot.platform_type}",
            f"Branch: {snapshot.branch}",
            f"Head SHA: {snapshot.head_sha}",
            f"Default branch: {snapshot.default_branch}",
            f"Snapshot digest: {snapshot.snapshot_digest}",
            *rules,
            *examples,
            "Available tools JSON:",
            tool_gateway.tool_signature(),
            "Project docs available:",
            ", ".join(sorted(snapshot.project_docs_summary)) or "-",
            "Recent commits:",
            "\n".join(snapshot.recent_commits_summary) or "-",
        ]
        return "\n".join(lines)

    @staticmethod
    def _append_history(history: str, entry: str) -> str:
        if not history:
            return str(entry)
        return f"{history}\n\n{entry}"

    def _update_memory_from_tool(
        self,
        *,
        memory_state: dict[str, Any],
        snapshot: Any,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_output: str,
    ) -> dict[str, Any]:
        updated = normalize_memory_state(memory_state)
        if tool_name not in {"read_file", "read_project_doc"}:
            return updated

        path = str(tool_args.get("path") or tool_args.get("name") or "").strip()
        if not path:
            return updated
        recent_files = [item for item in updated["working"]["recent_files"] if item != path]
        recent_files.append(path)
        updated["working"]["recent_files"] = recent_files[-8:]

        file_version = ""
        if tool_name == "read_file":
            file_entry = snapshot.file_tree_summary.get("files", {}).get(path)
            if isinstance(file_entry, dict):
                file_version = str(file_entry.get("file_version", ""))
        else:
            doc_entry = snapshot.project_docs_summary.get(path)
            if isinstance(doc_entry, dict):
                file_version = str(doc_entry.get("file_version", ""))
        updated["file_summaries"][path] = {
            "summary": self._clip_text(tool_output),
            "branch": snapshot.branch,
            "head_sha": snapshot.head_sha,
            "file_version": file_version,
            "updated_at": datetime.now(UTC).isoformat(),
            "source": f"tool:{tool_name}",
        }
        return normalize_memory_state(updated)

    def _update_memory_from_final(
        self,
        *,
        memory_state: dict[str, Any],
        user_message: str,
        final_answer: str,
    ) -> dict[str, Any]:
        updated = normalize_memory_state(memory_state)
        updated["working"]["task_summary"] = self._clip_text(user_message, limit=300)
        next_note_index = int(updated.get("next_note_index", 0))
        updated["episodic_notes"].append(
            {
                "text": self._clip_text(final_answer, limit=500),
                "tags": ["final_answer"],
                "source": "assistant",
                "created_at": datetime.now(UTC).isoformat(),
                "note_index": next_note_index,
                "kind": "episodic",
            }
        )
        updated["next_note_index"] = next_note_index + 1
        updated["episodic_notes"] = updated["episodic_notes"][-12:]
        return normalize_memory_state(updated)

    @staticmethod
    def _validate_final_answer(
        *,
        final_answer: str,
        user_message: str,
        history_text: str,
        tool_steps: int,
    ) -> str | None:
        normalized_answer = " ".join(str(final_answer).split())
        lowered_answer = normalized_answer.lower()
        lowered_request = str(user_message).lower()
        lowered_history = str(history_text).lower()

        premature_phrases = (
            "请让我查看",
            "请先让我查看",
            "需要先读",
            "需要先查看",
            "我还不能确定",
            "无法确定",
            "让我先读",
            "让我先查看",
        )
        if any(phrase in normalized_answer for phrase in premature_phrases):
            return (
                "Do not ask the user for permission to inspect repository files. "
                "Use a read-only tool yourself, or answer directly if you already have enough evidence."
            )

        if (
            tool_steps == 0
            and ("入口" in str(user_message) or "entrypoint" in lowered_request)
            and ("api.py" in lowered_answer or "main.py" in lowered_answer or "entry" in lowered_answer)
        ):
            return (
                "You mentioned a likely entry file without evidence. "
                "Call a repository tool first, then answer with evidence."
            )

        if (
            tool_steps == 0
            and ("上一轮" in str(user_message) or "刚才" in str(user_message) or "previous" in lowered_request)
            and not lowered_history.strip()
        ):
            return (
                "This is a follow-up question, but you answered without using the available conversation history. "
                "Re-read History and then either use a focused tool or answer directly."
            )

        return None

    @staticmethod
    def _clip_text(text: str, *, limit: int = 240) -> str:
        normalized = " ".join(str(text).split())
        if len(normalized) <= limit:
            return normalized
        if limit <= 3:
            return normalized[:limit]
        return normalized[: limit - 3] + "..."

    @staticmethod
    def _completion_metadata(
        *,
        llm_config: LLMConfig,
        attempts: int,
        tool_steps: int,
    ) -> dict[str, Any]:
        return {
            "provider": llm_config.provider,
            "model": llm_config.model,
            "attempts": attempts,
            "tool_steps": tool_steps,
        }

    @staticmethod
    def _build_artifacts(
        *,
        prompt_metadata: dict[str, Any],
        initial_memory_state: dict[str, Any],
        memory_state: dict[str, Any],
        report_payload: dict[str, Any],
        snapshot: Any,
    ) -> list[dict[str, Any]]:
        return [
            {
                "artifact_type": "prompt_context",
                "name": "prompt_context",
                "content": {
                    "prefix": prompt_metadata.get("prefix", ""),
                    "memory": prompt_metadata.get("memory", ""),
                    "relevant_memory": prompt_metadata.get("relevant_memory", ""),
                    "history": prompt_metadata.get("history", ""),
                    "current_request": prompt_metadata.get("current_request", ""),
                    "sections": prompt_metadata.get("sections", {}),
                    "budget_reductions": prompt_metadata.get("budget_reductions", []),
                    "prompt_chars": prompt_metadata.get("prompt_chars"),
                    "prompt_budget_chars": prompt_metadata.get("prompt_budget_chars"),
                },
                "metadata": {},
            },
            {
                "artifact_type": "memory_delta",
                "name": "memory_delta",
                "content": {
                    "before": initial_memory_state,
                    "after": memory_state,
                },
                "metadata": {},
            },
            {
                "artifact_type": "run_report",
                "name": "run_report",
                "content": report_payload,
                "metadata": {"note": DEFAULT_REPORT_NOTE if not report_payload.get("final_answer") else ""},
            },
            {
                "artifact_type": "snapshot_summary",
                "name": "snapshot_summary",
                "content": {
                    "project_id": snapshot.project_id,
                    "platform_type": snapshot.platform_type,
                    "branch": snapshot.branch,
                    "head_sha": snapshot.head_sha,
                    "default_branch": snapshot.default_branch,
                    "snapshot_digest": snapshot.snapshot_digest,
                    "project_docs_summary": snapshot.project_docs_summary,
                    "recent_commits_summary": snapshot.recent_commits_summary,
                },
                "metadata": {},
            },
        ]
