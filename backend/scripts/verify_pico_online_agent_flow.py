from __future__ import annotations

import json
import sys
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent.event_recorder import AgentEventRecorder
from app.agent.run_service import AgentRunService
from app.agent.snapshot_service import RepositorySnapshotService
from app.agent.tool_gateway import AgentToolGateway
from app.api.routes.agent import _iter_sse
from app.db.base import Base
import app.db.models  # noqa: F401
from app.db.models import AgentMessage, AgentRun, AgentRunEvent, AgentSession, Project
from app.services.agent_session_service import AgentSessionService

POSTGRES_ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
POSTGRES_TEST_DSN_TEMPLATE = "postgresql+psycopg://postgres:postgres@localhost:5432/{db_name}"
REPORT_PATH = Path(__file__).resolve().parents[2] / "docs/verification/2026-06-03-pico-online-agent-mvp.md"


@dataclass
class TurnResult:
    question: str
    run: AgentRun
    assistant_message: AgentMessage
    events: list[AgentRunEvent]


class FakeRepositoryProvider:
    def __init__(self) -> None:
        self.file_contents = {
            "backend/app/main.py": "\n".join(
                [
                    "from fastapi import FastAPI",
                    "from app.api.router import api_router",
                    "",
                    "app = FastAPI()",
                    'app.include_router(api_router, prefix="/api/v1")',
                ]
            ),
            "backend/app/api/router.py": "\n".join(
                [
                    "from fastapi import APIRouter",
                    "from app.api.routes.agent import router as agent_router",
                    "api_router = APIRouter()",
                    "api_router.include_router(agent_router)",
                ]
            ),
            "backend/app/security/deps.py": "\n".join(
                [
                    "def get_current_user(...):",
                    "    return user",
                    "",
                    "def require_permission(permission_code: str):",
                    "    return dependency",
                ]
            ),
            "README.md": "\n".join(
                [
                    "# AI Code Review Platform",
                    "",
                    "This repository contains the backend, frontend, and docs.",
                ]
            ),
        }

    def get_head_sha(self, *, ref: str) -> str:
        return f"{ref}-fake-head"

    def get_file_tree(self, *, ref: str) -> list[dict[str, str]]:
        del ref
        return [
            {"path": "README.md", "type": "file"},
            {"path": "backend", "type": "dir"},
            {"path": "backend/app", "type": "dir"},
            {"path": "backend/app/main.py", "type": "file"},
            {"path": "backend/app/api/router.py", "type": "file"},
            {"path": "backend/app/security/deps.py", "type": "file"},
        ]

    def get_snapshot_overview(self, *, ref: str) -> dict[str, str]:
        del ref
        return {"readme": self.file_contents["README.md"]}

    def get_recent_commit_records(self, *, limit: int) -> list[dict[str, str]]:
        return [
            {"id": "c1", "message": "feat: add repo assistant"},
            {"id": "c2", "message": "test: verify pico online flow"},
        ][:limit]

    def list_files(self, *, path: str, ref: str) -> str:
        del ref
        normalized = path.strip("/") or "."
        paths = []
        for item in self.get_file_tree(ref="main"):
            current = str(item["path"]).strip("/")
            if normalized == "." or current == normalized or current.startswith(f"{normalized}/"):
                paths.append(current)
        return "\n".join(paths)

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        del ref
        content = self.file_contents.get(path, "")
        lines = content.splitlines()
        if start > len(lines):
            return ""
        return "\n".join(lines[start - 1 : end])

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        del ref
        results: list[str] = []
        normalized = path.strip("/") or "."
        for file_path, content in self.file_contents.items():
            if normalized != "." and not file_path.startswith(normalized):
                continue
            for index, line in enumerate(content.splitlines(), start=1):
                if pattern.lower() in line.lower():
                    results.append(f"{file_path}:{index}:{line}")
        return "\n".join(results) or "no matches"

    def get_project_overview(self) -> str:
        return self.file_contents["README.md"]

    def get_recent_commits(self, *, limit: int) -> str:
        return "\n".join(
            f"{item['id']} {item['message']}"
            for item in self.get_recent_commit_records(limit=limit)
        )


class FakeConversationModel:
    def __init__(self) -> None:
        self.prompts: list[dict[str, object]] = []

    def complete(self, *, prompt: str, metadata: dict[str, object]) -> str:
        self.prompts.append({"prompt": prompt, "metadata": metadata})
        request = _extract_current_request(prompt)

        if "这个仓库的后端入口在哪里" in request:
            if "from fastapi import FastAPI" not in prompt:
                return json.dumps(
                    {
                        "tool": {
                            "name": "read_file",
                            "args": {
                                "path": "backend/app/main.py",
                                "start": 1,
                                "end": 20,
                                "ref": "main",
                            },
                        }
                    }
                )
            return "后端入口在 `backend/app/main.py`，FastAPI 应用和 `api_router` 都从这里挂载。"

        if "刚才说到的入口和认证链路有什么关系" in request:
            if "require_permission" not in prompt:
                return json.dumps(
                    {
                        "tool": {
                            "name": "search",
                            "args": {
                                "pattern": "require_permission",
                                "path": "backend/app",
                                "ref": "main",
                            },
                        }
                    }
                )
            return (
                "刚才提到的入口会把 `api_router` 接进应用，认证链路主要在 "
                "`backend/app/security/deps.py` 的 `get_current_user` 和 `require_permission`。"
            )

        if "基于上一轮内容，总结我应该先读哪几个文件" in request:
            if "def get_current_user" not in prompt:
                return json.dumps(
                    {
                        "tool": {
                            "name": "read_file",
                            "args": {
                                "path": "backend/app/security/deps.py",
                                "start": 1,
                                "end": 40,
                                "ref": "main",
                            },
                        }
                    }
                )
            return (
                "基于上一轮内容，建议先读 `backend/app/main.py`、`backend/app/api/router.py` "
                "和 `backend/app/security/deps.py`。上一轮我们已经确认了入口挂载和认证校验就在这几处汇合。"
            )

        return "未命中的测试问题。"


@contextmanager
def temp_session_factory() -> Generator[sessionmaker[Session], None, None]:
    db_name = f"agent_flow_{uuid4().hex[:8]}"
    with psycopg.connect(POSTGRES_ADMIN_DSN, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    engine = create_engine(
        POSTGRES_TEST_DSN_TEMPLATE.format(db_name=db_name),
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        class_=Session,
    )

    try:
        yield session_factory
    finally:
        engine.dispose()
        with psycopg.connect(POSTGRES_ADMIN_DSN, autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()"
                ),
                [db_name],
            )
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))


def main() -> int:
    questions = [
        "这个仓库的后端入口在哪里？",
        "刚才说到的入口和认证链路有什么关系？",
        "基于上一轮内容，总结我应该先读哪几个文件。",
    ]
    provider = FakeRepositoryProvider()
    model = FakeConversationModel()

    with temp_session_factory() as session_factory:
        with session_factory() as db:
            project = Project(
                name="Agent Verification Project",
                key="agent-verification-project",
                platform_type="github",
                repo_url="https://example.com/agent-verification.git",
                default_branch="main",
                description="Verification project for the repo assistant flow.",
                review_enabled=True,
                settings={},
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            snapshot = RepositorySnapshotService(db).ensure_ready_snapshot(
                project=project,
                provider=provider,
            )
            session_service = AgentSessionService(db)
            agent_session = session_service.create_session(
                project=project,
                title="验证会话",
                created_by=None,
                snapshot=snapshot,
            )
            run_service = AgentRunService(
                session=db,
                model_client=model,
                tool_gateway=AgentToolGateway(provider=provider),
                event_recorder=AgentEventRecorder(db),
                session_service=session_service,
            )

            turns: list[TurnResult] = []
            for question in questions:
                _, assistant_message, run = session_service.create_message_pair_and_run(
                    session=agent_session,
                    content=question,
                )
                completed_run = run_service.run(run.id)
                db.refresh(agent_session)
                db.refresh(assistant_message)
                events = db.scalars(
                    select(AgentRunEvent)
                    .where(AgentRunEvent.run_id == completed_run.id)
                    .order_by(AgentRunEvent.sequence.asc())
                ).all()
                turns.append(
                    TurnResult(
                        question=question,
                        run=completed_run,
                        assistant_message=assistant_message,
                        events=list(events),
                    )
                )

            checks = build_checks(agent_session=agent_session, turns=turns)
            report = build_report(
                turns=turns,
                checks=checks,
                memory_state=agent_session.memory_state,
            )
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(report, encoding="utf-8")

            print(report)
            print(f"\nReport written to {REPORT_PATH}")
            return 0 if all(item["passed"] for item in checks) else 1


def build_checks(*, agent_session: AgentSession, turns: list[TurnResult]) -> list[dict[str, object]]:
    all_events = [event for turn in turns for event in turn.events]
    sse_text = "".join(_iter_sse(all_events))
    prompt_sections = [turn.run.prompt_metadata.get("sections", {}) for turn in turns]

    checks = [
        {
            "name": "正常输出",
            "passed": all(
                turn.assistant_message.status == "completed"
                and bool(turn.run.final_answer)
                and turn.run.status == "completed"
                for turn in turns
            ),
            "details": "三轮 assistant message 均完成，run 状态为 completed，final_answer 非空。",
        },
        {
            "name": "流式输出格式",
            "passed": (
                all(
                    [event.sequence for event in turn.events]
                    == sorted(event.sequence for event in turn.events)
                    for turn in turns
                )
                and "event: run_started" in sse_text
                and "event: assistant_message" in sse_text
                and "event: final" in sse_text
                and "data:" in sse_text
            ),
            "details": "事件 sequence 单调递增，SSE 回放包含 id/event/data 三种字段。",
        },
        {
            "name": "工具调用",
            "passed": any(
                event.event_type == "tool_result"
                and str(event.payload.get("name")) in {"read_file", "search"}
                for event in all_events
            ),
            "details": "至少一轮出现 read_file 或 search 的 tool_result。",
        },
        {
            "name": "Prompt 组装",
            "passed": all(
                {"prefix", "memory", "relevant_memory", "history", "current_request"}.issubset(
                    sections.keys()
                )
                and "Workspace:" in str(turn.run.prompt_metadata.get("prompt", ""))
                and "Instructions:" in str(turn.run.prompt_metadata.get("prompt", ""))
                for turn, sections in zip(turns, prompt_sections, strict=True)
            ),
            "details": "每轮 prompt_metadata 都包含 section chars 元数据与完整 prompt 文本。",
        },
        {
            "name": "Memory 更新",
            "passed": (
                bool(agent_session.memory_state.get("working", {}).get("recent_files"))
                and "基于上一轮内容" in str(
                    agent_session.memory_state.get("working", {}).get("task_summary", "")
                )
            ),
            "details": "session.memory_state 里保留 recent_files，task_summary 反映第三轮主题。",
        },
        {
            "name": "多轮连贯",
            "passed": (
                "这个仓库的后端入口在哪里" in str(turns[1].run.prompt_metadata.get("prompt", ""))
                and "刚才说到的入口和认证链路有什么关系" in str(
                    turns[2].run.prompt_metadata.get("prompt", "")
                )
                and "上一轮" in str(turns[2].run.final_answer or "")
            ),
            "details": "第二轮 prompt 能看到第一轮，第三轮 prompt 能看到第二轮，最终回答显式引用上一轮。",
        },
    ]
    return checks


def build_report(
    *,
    turns: list[TurnResult],
    checks: list[dict[str, object]],
    memory_state: dict[str, object],
) -> str:
    lines = [
        "# Pico Online Agent MVP Verification",
        "",
        "## Commands",
        "",
        "- `cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`",
        "- `cd frontend && npm test`",
        "- `cd backend && python scripts/verify_pico_online_agent_flow.py`",
        "",
        "## Check Results",
        "",
    ]
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- `{status}` {check['name']}: {check['details']}")

    lines.extend(
        [
            "",
            "## Conversation",
            "",
        ]
    )
    for index, turn in enumerate(turns, start=1):
        tool_names = [
            str(event.payload.get("name"))
            for event in turn.events
            if event.event_type == "tool_result"
        ]
        lines.extend(
            [
                f"### Turn {index}",
                "",
                f"- User: {turn.question}",
                f"- Assistant: {turn.run.final_answer}",
                f"- Stop reason: `{turn.run.stop_reason}`",
                f"- Tool events: {', '.join(tool_names) if tool_names else 'none'}",
                f"- Prompt chars: {turn.run.prompt_metadata.get('prompt_chars')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Final Memory",
            "",
            "```json",
            json.dumps(memory_state, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _extract_current_request(prompt: str) -> str:
    marker = "Current user request:\n"
    if marker not in prompt:
        return prompt
    return prompt.split(marker, 1)[1].strip()


if __name__ == "__main__":
    raise SystemExit(main())
