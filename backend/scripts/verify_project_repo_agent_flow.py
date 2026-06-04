from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func, select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings
from app.core.env_compat import load_backend_env_compat
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
from app.db.session import SessionLocal
from app.llm.provider import load_llm_config


DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "verification" / "2026-06-04-repo-agent-verification.md"

load_backend_env_compat()


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoundExecutionResult:
    index: int
    question: str
    user_message: dict[str, Any]
    raw_sse_chunks: list[str]
    sse_events: list[dict[str, Any]]
    run_record: dict[str, Any]
    assistant_message: dict[str, Any]


def build_questions(max_rounds: int = 3) -> list[str]:
    questions = [
        "这个仓库的后端入口在哪里？",
        "刚才说到的入口初始化之后，路由是怎么注册进去的？",
        "基于上一轮内容，总结我应该先读哪几个文件。",
    ]
    return questions[: max(0, int(max_rounds))]


def build_round_question(index: int, previous_results: list[RoundExecutionResult]) -> str:
    questions = build_questions(max_rounds=max(index, 0))
    if index <= 1 or not previous_results:
        return questions[0]

    previous_answer = str(previous_results[-1].assistant_message.get("content") or "")
    candidate_paths = _extract_candidate_paths(previous_answer)

    if index == 2:
        focus = "、".join(candidate_paths[:2]) or "api.py、相邻的初始化模块"
        return (
            f"围绕上一轮提到的 {focus}，入口初始化之后，路由是怎么注册进去的？"
            "请优先顺着相邻导入链路说明，不要做全仓库泛搜。"
        )

    focus = "、".join(candidate_paths[:3]) or "入口文件、初始化模块、路由模块"
    return (
        f"基于前两轮提到的 {focus}，总结我应该按什么顺序先读 3 到 5 个文件，"
        "每个文件各自解决什么问题。"
    )


def classify_sse_payload(payload: str) -> dict[str, Any]:
    event_name = ""
    data_lines: list[str] = []
    for line in payload.splitlines():
        if line.startswith("event:"):
            event_name = line.partition(":")[2].strip()
        elif line.startswith("data:"):
            data_lines.append(line.partition(":")[2].strip())
    is_valid = bool(event_name and data_lines)
    parsed_data: dict[str, Any] | None = None
    if data_lines:
        try:
            parsed = json.loads("\n".join(data_lines))
            if isinstance(parsed, dict):
                parsed_data = parsed
        except json.JSONDecodeError:
            parsed_data = None
    return {
        "event": event_name,
        "data": parsed_data or {},
        "is_valid": is_valid,
    }


def validate_report_checks(checks: dict[str, bool]) -> list[str]:
    check_messages = {
        "has_final_output": "缺少最终回答输出",
        "sse_format_ok": "SSE 格式或事件类型不符合预期",
        "tool_called": "未观察到真实工具调用",
        "prompt_assembled": "prompt_metadata 缺少预期字段或多轮未增长",
        "memory_updated": "memory_state 未按预期更新",
        "multi_turn_continuity": "多轮对话未体现上一轮上下文",
        "db_persisted": "数据库落库结果不完整",
    }
    return [
        message
        for key, message in check_messages.items()
        if not bool(checks.get(key))
    ]


def evaluate_prompt_assembled(round_results: list[RoundExecutionResult]) -> bool:
    if not round_results:
        return False

    for index, result in enumerate(round_results):
        prompt_metadata = dict(result.run_record.get("prompt_metadata") or {})
        if not all(
            isinstance(prompt_metadata.get(key), str)
            for key in ("prefix", "memory", "relevant_memory", "history", "current_request")
        ):
            return False
        if prompt_metadata["current_request"] != result.question:
            return False
        if index == 0:
            continue

        history_text = str(prompt_metadata.get("history") or "")
        prior_result = round_results[index - 1]
        prior_user = str(prior_result.question or "").strip()
        prior_answer = str(prior_result.assistant_message.get("content") or "").strip()
        if prior_user and prior_user not in history_text:
            return False
        if prior_answer:
            prior_answer_terms = [
                term
                for term in _extract_candidate_terms(prior_answer)
                if len(term) >= 4
            ][:5]
            if not prior_answer_terms and prior_answer[:80]:
                prior_answer_terms = [prior_answer[:80]]
            if prior_answer_terms and not any(term in history_text for term in prior_answer_terms):
                return False
    return True


def run_preflight_checks(*, project_id: int, branch: str, base_url: str) -> PreflightResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        llm_config = load_llm_config(default_provider="openai")
    except RuntimeError as exc:
        errors.append(str(exc))
        llm_config = None

    if llm_config is not None:
        missing_env = [
            env_name
            for env_name in llm_config.required_env
            if not os.getenv(env_name)
        ]
        if missing_env:
            errors.append(f"缺少 LLM 必需环境变量: {', '.join(missing_env)}")

    if not str(branch).strip():
        errors.append("branch 不能为空")
    if not str(base_url).strip():
        errors.append("base_url 不能为空")

    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.id == project_id))
        if project is None:
            errors.append(f"项目不存在: {project_id}")
        else:
            if project.platform_type == "github" and not os.getenv("GITHUB_ACCESS_TOKEN"):
                errors.append("缺少 GITHUB_ACCESS_TOKEN")
            if project.platform_type == "gitlab" and not os.getenv("GITLAB_ACCESS_TOKEN"):
                errors.append("缺少 GITLAB_ACCESS_TOKEN")
            if project.default_branch != branch:
                warnings.append(
                    f"当前验证分支为 {branch}，项目默认分支为 {project.default_branch}"
                )

        bootstrap_username = Settings().bootstrap_admin_username
        user_exists = db.scalar(select(User.id).where(User.username == bootstrap_username))
        if user_exists is None:
            warnings.append(
                f"未找到 bootstrap 管理员用户 {bootstrap_username}，登录可能失败"
            )

    return PreflightResult(ok=not errors, errors=errors, warnings=warnings)


def _api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/api/v1{path}"


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = Request(
        url,
        method=method,
        headers=request_headers,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc
    if not body.strip():
        return {}
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON payload from {url}: {type(parsed).__name__}")
    return parsed


def login(base_url: str) -> str:
    settings = Settings()
    body = _request_json(
        method="POST",
        url=_api_url(base_url, "/auth/login"),
        payload={
            "username": settings.bootstrap_admin_username,
            "password": settings.bootstrap_admin_password,
        },
    )
    token = str(body.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("登录成功但未返回 access_token")
    return token


def create_session(*, base_url: str, project_id: int, branch: str, access_token: str) -> dict[str, Any]:
    return _request_json(
        method="POST",
        url=_api_url(base_url, f"/projects/{project_id}/agent/sessions"),
        payload={
            "title": f"Repo Agent Verification {int(time.time())}",
            "branch": branch,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )


def send_message(
    *,
    base_url: str,
    project_id: int,
    session_id: int,
    question: str,
    access_token: str,
) -> dict[str, Any]:
    return _request_json(
        method="POST",
        url=_api_url(base_url, f"/projects/{project_id}/agent/sessions/{session_id}/messages"),
        payload={"content": question},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _split_sse_chunks(buffer: str) -> tuple[list[str], str]:
    chunks: list[str] = []
    remainder = buffer
    while True:
        boundary = remainder.find("\n\n")
        if boundary < 0:
            break
        chunk = remainder[:boundary]
        remainder = remainder[boundary + 2 :]
        if chunk.strip():
            chunks.append(chunk)
    return chunks, remainder


def consume_sse_until_final(
    *,
    base_url: str,
    project_id: int,
    session_id: int,
    access_token: str,
    after_message_id: int,
    baseline_event_id: int,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    url = _api_url(
        base_url,
        (
            f"/projects/{project_id}/agent/sessions/{session_id}/stream"
            f"?after_event_id={baseline_event_id}&after_message_id={after_message_id}"
        ),
    )
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {access_token}",
        },
    )
    started_at = time.time()
    collected: list[dict[str, Any]] = []
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            buffer = ""
            while True:
                if time.time() - started_at > timeout_seconds:
                    raise TimeoutError(f"SSE consume timed out after {timeout_seconds}s")
                chunk_bytes = response.read(1024)
                if not chunk_bytes:
                    break
                buffer += chunk_bytes.decode("utf-8", errors="replace")
                chunks, buffer = _split_sse_chunks(buffer)
                for raw_chunk in chunks:
                    parsed = classify_sse_payload(raw_chunk)
                    parsed["raw"] = raw_chunk
                    collected.append(parsed)
                    event_id = int(parsed["data"].get("id") or 0)
                    if (
                        parsed["event"] in {"final_answer", "run_failed"}
                        and event_id > baseline_event_id
                    ):
                        return collected
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GET {url} failed: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc
    return collected


def load_run_records(*, session_id: int, run_id: int | None = None) -> dict[str, Any]:
    with SessionLocal() as db:
        run_query = select(AgentRun).where(AgentRun.session_id == session_id)
        if run_id is not None:
            run_query = run_query.where(AgentRun.id == run_id)
        run = db.scalar(run_query.order_by(AgentRun.id.desc()))
        if run is None:
            raise RuntimeError(f"未找到 run 记录: session_id={session_id}, run_id={run_id}")

        events = db.scalars(
            select(AgentRunEvent)
            .where(AgentRunEvent.run_id == run.id)
            .order_by(AgentRunEvent.sequence.asc(), AgentRunEvent.id.asc())
        ).all()
        artifacts = db.scalars(
            select(AgentArtifact)
            .where(AgentArtifact.run_id == run.id)
            .order_by(AgentArtifact.id.asc())
        ).all()
        assistant_message = db.scalar(
            select(AgentMessage).where(AgentMessage.id == run.assistant_message_id)
        )
        session_row = db.scalar(select(AgentSession).where(AgentSession.id == session_id))
        snapshot = None
        if run.head_sha:
            snapshot = db.scalar(
                select(RepositorySnapshot).where(
                    RepositorySnapshot.project_id == run.project_id,
                    RepositorySnapshot.branch == run.branch,
                    RepositorySnapshot.head_sha == run.head_sha,
                )
            )
        return {
            "run": run,
            "events": events,
            "artifacts": artifacts,
            "assistant_message": assistant_message,
            "session": session_row,
            "snapshot": snapshot,
        }


def _round_record_to_dict(record: dict[str, Any]) -> dict[str, Any]:
    run = record["run"]
    assistant_message = record["assistant_message"]
    session_row = record["session"]
    return {
        "run_id": run.id,
        "status": run.status,
        "stop_reason": run.stop_reason,
        "last_tool": run.last_tool,
        "tool_steps": run.tool_steps,
        "attempts": run.attempts,
        "head_sha": run.head_sha,
        "prompt_metadata": dict(run.prompt_metadata or {}),
        "completion_metadata": dict(run.completion_metadata or {}),
        "event_types": [event.event_type for event in record["events"]],
        "artifacts": [
            {
                "artifact_type": artifact.artifact_type,
                "name": artifact.name,
                "content": artifact.content,
            }
            for artifact in record["artifacts"]
        ],
        "assistant_message": {
            "id": getattr(assistant_message, "id", None),
            "status": getattr(assistant_message, "status", None),
            "content": getattr(assistant_message, "content", None),
        },
        "session": {
            "id": getattr(session_row, "id", None),
            "last_head_sha": getattr(session_row, "last_head_sha", None),
            "last_workspace_fingerprint": getattr(session_row, "last_workspace_fingerprint", None),
            "last_runtime_identity_hash": getattr(session_row, "last_runtime_identity_hash", None),
            "memory_state": dict(getattr(session_row, "memory_state", {}) or {}),
        },
        "snapshot_exists": record["snapshot"] is not None,
    }


def render_report(
    *,
    project_id: int,
    branch: str,
    session_id: int,
    checks: dict[str, bool],
    round_results: list[RoundExecutionResult],
    preflight: PreflightResult,
) -> str:
    failures = validate_report_checks(checks)
    lines = [
        "# Repo Agent Verification",
        "",
        f"- Project ID: `{project_id}`",
        f"- Branch: `{branch}`",
        f"- Session ID: `{session_id}`",
        f"- Preflight: `{'OK' if preflight.ok else 'FAILED'}`",
        "",
        "## Acceptance Checks",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{'PASS' if value else 'FAIL'}`")
    lines.extend(["", "## Preflight Warnings"])
    lines.extend([f"- {item}" for item in preflight.warnings] or ["- (none)"])
    lines.extend(["", "## Failures"])
    lines.extend([f"- {item}" for item in failures] or ["- (none)"])
    lines.extend(["", "## Rounds"])
    for result in round_results:
        lines.extend(
            [
                f"### Round {result.index}",
                f"- Question: {result.question}",
                f"- User Message ID: `{result.user_message.get('id')}`",
                f"- Run ID: `{result.run_record['run_id']}`",
                f"- Run Status: `{result.run_record['status']}`",
                f"- Last Tool: `{result.run_record['last_tool']}`",
                f"- Event Types: `{', '.join(result.run_record['event_types'])}`",
                f"- Assistant Status: `{result.assistant_message['status']}`",
                f"- Assistant Answer: {result.assistant_message['content'] or '(empty)' }",
                f"- SSE Chunks: `{len(result.raw_sse_chunks)}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_report(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _extract_text_artifact(artifacts: list[dict[str, Any]], artifact_type: str) -> dict[str, Any]:
    for artifact in artifacts:
        if artifact.get("artifact_type") != artifact_type:
            continue
        try:
            parsed = json.loads(str(artifact.get("content") or "{}"))
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _collect_baseline(session_id: int) -> dict[str, int]:
    with SessionLocal() as db:
        max_event_id = db.scalar(
            select(func.max(AgentRunEvent.id)).where(AgentRunEvent.session_id == session_id)
        )
        max_message_id = db.scalar(
            select(func.max(AgentMessage.id)).where(AgentMessage.session_id == session_id)
        )
        return {
            "event_id": int(max_event_id or 0),
            "message_id": int(max_message_id or 0),
        }


def _extract_candidate_terms(text: str) -> list[str]:
    candidates: list[str] = []
    normalized_text = str(text)
    for punct in ("，", "。", "；", "：", "（", "）", "《", "》", "、"):
        normalized_text = normalized_text.replace(punct, " ")
    for token in normalized_text.replace("\n", " ").split():
        cleaned = token.strip("`'\",:;()[]{}")
        if "/" in cleaned or "." in cleaned:
            candidates.append(cleaned)
    return candidates[:12]


def _extract_candidate_paths(text: str) -> list[str]:
    candidates: list[str] = []
    for token in _extract_candidate_terms(text):
        cleaned = str(token).strip()
        if any(char in cleaned for char in ('"', "'", "(", ")")):
            continue
        if any("\u4e00" <= char <= "\u9fff" for char in cleaned):
            continue
        if ":" in cleaned:
            base, suffix = cleaned.rsplit(":", 1)
            if suffix.isdigit():
                cleaned = base
        cleaned = cleaned.strip("`'\",:;()[]{}<>。！？、，")
        if not cleaned or cleaned in candidates:
            continue
        if cleaned.endswith(".") and "/" not in cleaned:
            cleaned = cleaned[:-1]
        if ":" in cleaned:
            continue
        if cleaned.startswith(".") or cleaned.endswith(".env") or cleaned.startswith("conf/."):
            continue
        if cleaned.endswith(".py") or cleaned.endswith(".md"):
            candidates.append(cleaned)
            continue
        if "/" in cleaned and not cleaned.split("/", 1)[0].startswith("."):
            candidates.append(cleaned)
    return candidates[:8]


def execute_verification(
    *,
    project_id: int,
    branch: str,
    base_url: str,
    max_rounds: int,
    report_path: Path,
) -> tuple[dict[str, bool], list[RoundExecutionResult], PreflightResult, int]:
    preflight = run_preflight_checks(project_id=project_id, branch=branch, base_url=base_url)
    if not preflight.ok:
        raise RuntimeError("Preflight failed: " + "; ".join(preflight.errors))

    access_token = login(base_url)
    session_payload = create_session(
        base_url=base_url,
        project_id=project_id,
        branch=branch,
        access_token=access_token,
    )
    session_id = int(session_payload["id"])

    with SessionLocal() as db:
        session_row = db.scalar(select(AgentSession).where(AgentSession.id == session_id))
        initial_memory_state = dict(getattr(session_row, "memory_state", {}) or {})

    round_results: list[RoundExecutionResult] = []

    for index in range(1, max_rounds + 1):
        question = build_round_question(index, round_results)
        baseline = _collect_baseline(session_id)
        stream_events: list[dict[str, Any]] = []
        thread_error: list[BaseException] = []

        def _consume() -> None:
            try:
                stream_events.extend(
                    consume_sse_until_final(
                        base_url=base_url,
                        project_id=project_id,
                        session_id=session_id,
                        access_token=access_token,
                        after_message_id=baseline["message_id"],
                        baseline_event_id=baseline["event_id"],
                    )
                )
            except BaseException as exc:  # noqa: BLE001
                thread_error.append(exc)

        consumer = threading.Thread(target=_consume, daemon=True)
        consumer.start()
        time.sleep(0.2)
        user_message = send_message(
            base_url=base_url,
            project_id=project_id,
            session_id=session_id,
            question=question,
            access_token=access_token,
        )
        consumer.join(timeout=DEFAULT_TIMEOUT_SECONDS)
        if consumer.is_alive():
            raise RuntimeError(f"Round {index} SSE consumer did not finish in time")
        if thread_error:
            raise RuntimeError(f"Round {index} SSE consumer failed: {thread_error[0]}")

        run_record = _round_record_to_dict(
            load_run_records(
                session_id=session_id,
                run_id=int(user_message.get("run_id") or 0) or None,
            )
        )
        assistant_message = dict(run_record["assistant_message"])
        round_results.append(
            RoundExecutionResult(
                index=index,
                question=question,
                user_message=user_message,
                raw_sse_chunks=[event.get("raw", "") for event in stream_events],
                sse_events=stream_events,
                run_record=run_record,
                assistant_message=assistant_message,
            )
        )

    with SessionLocal() as db:
        session_row = db.scalar(select(AgentSession).where(AgentSession.id == session_id))
        messages = db.scalars(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.sequence.asc(), AgentMessage.id.asc())
        ).all()
        runs = db.scalars(
            select(AgentRun)
            .where(AgentRun.session_id == session_id)
            .order_by(AgentRun.id.asc())
        ).all()
        run_events = db.scalars(
            select(AgentRunEvent)
            .where(AgentRunEvent.session_id == session_id)
            .order_by(AgentRunEvent.sequence.asc(), AgentRunEvent.id.asc())
        ).all()
        snapshots = db.scalars(
            select(RepositorySnapshot).where(RepositorySnapshot.project_id == project_id)
        ).all()
        final_memory_state = dict(getattr(session_row, "memory_state", {}) or {})

    checks = {
        "has_final_output": all(
            result.assistant_message.get("status") == "completed"
            and str(result.assistant_message.get("content") or "").strip()
            for result in round_results
        ),
        "sse_format_ok": all(
            any(item["event"] == "run_started" for item in result.sse_events)
            and any(item["event"] == "assistant_delta" for item in result.sse_events)
            and any(item["event"] == "final_answer" for item in result.sse_events)
            and all(item["is_valid"] for item in result.sse_events if item.get("raw"))
            for result in round_results
        ),
        "tool_called": (
            any("tool_called" in result.run_record["event_types"] for result in round_results)
            and any("tool_result" in result.run_record["event_types"] for result in round_results)
        ),
        "prompt_assembled": False,
        "memory_updated": False,
        "multi_turn_continuity": False,
        "db_persisted": False,
    }

    checks["prompt_assembled"] = evaluate_prompt_assembled(round_results)

    memory_changed = initial_memory_state != final_memory_state
    recent_files = (
        final_memory_state.get("working", {}).get("recent_files", [])
        if isinstance(final_memory_state, dict)
        else []
    )
    checks["memory_updated"] = bool(
        recent_files
        and memory_changed
        and (
            final_memory_state.get("episodic_notes")
            or final_memory_state.get("file_summaries")
            or final_memory_state.get("working", {}).get("task_summary")
        )
    )

    continuity_terms = _extract_candidate_terms(round_results[0].assistant_message.get("content", ""))
    later_answers = " ".join(
        str(result.assistant_message.get("content") or "")
        for result in round_results[1:]
    )
    continuity_hit = bool(
        any(term and term in later_answers for term in continuity_terms)
        or "认证" in later_answers
        or "入口" in later_answers
    )
    prompt_history_hit = (
        len(round_results) >= 2
        and round_results[1].run_record["prompt_metadata"].get("history", "").find(round_results[0].question) >= 0
    )
    checks["multi_turn_continuity"] = continuity_hit and prompt_history_hit

    artifact_type_set = {
        artifact["artifact_type"]
        for result in round_results
        for artifact in result.run_record["artifacts"]
    }
    db_sequences = [event.sequence for event in run_events]
    checks["db_persisted"] = bool(
        session_row is not None
        and getattr(session_row, "last_head_sha", None)
        and getattr(session_row, "last_workspace_fingerprint", None)
        and getattr(session_row, "last_runtime_identity_hash", None)
        and len([message for message in messages if message.role == "user"]) >= max_rounds
        and len([message for message in messages if message.role == "assistant"]) >= max_rounds
        and len(runs) >= max_rounds
        and all(run.status == "completed" for run in runs[:max_rounds])
        and db_sequences == sorted(db_sequences)
        and {"prompt_context", "memory_delta", "run_report"} <= artifact_type_set
        and bool(snapshots)
    )

    report = render_report(
        project_id=project_id,
        branch=branch,
        session_id=session_id,
        checks=checks,
        round_results=round_results,
        preflight=preflight,
    )
    write_report(report_path, report)
    return checks, round_results, preflight, session_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Repo Agent real multi-turn flow.")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--branch", type=str, required=True)
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    try:
        checks, _, _, session_id = execute_verification(
            project_id=args.project_id,
            branch=args.branch,
            base_url=args.base_url,
            max_rounds=args.max_rounds,
            report_path=args.report_path,
        )
    except Exception as exc:  # noqa: BLE001
        message = f"Repo Agent verification failed: {exc}"
        print(message, file=sys.stderr)
        if args.report_path:
            write_report(
                args.report_path,
                "# Repo Agent Verification\n\n- Result: `FAILED`\n- Error: "
                f"{message}\n",
            )
        return 1

    failures = validate_report_checks(checks)
    print(f"Repo Agent verification session_id={session_id}")
    for key, value in checks.items():
        print(f"- {key}: {'PASS' if value else 'FAIL'}")
    if failures:
        for item in failures:
            print(f"- failure: {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
