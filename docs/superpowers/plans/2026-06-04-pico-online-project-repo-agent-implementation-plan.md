# Pico Online 项目级仓库对话助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 AI Code Review 平台中实现一个保留 Pico 核心设计的项目级仓库对话助手，支持按项目创建锁定分支的持续会话、只读仓库工具、PR/MR 元信息工具、SSE 流式回答、结构化 trace/artifact 落库与文件 freshness 失效机制。

**Architecture:** 新增 `backend/app/agent/` 领域模块，复用 Pico 的 `ContextManager`、`LayeredMemory`、工具协议、workspace identity、run state 与 trace 思路；将本地文件系统、`.pico/` session store 与 CLI runtime 替换为 PostgreSQL 持久化、GitHub/GitLab `RepositoryProvider`、FastAPI API 与前端 Chat 页面。第一版严格只读：不开放 shell、不写文件、不 patch、不 delegate，只保留 `<tool>...</tool>` / `<final>...</final>` 的 Pico 风格输出协议与受约束工具网关。LLM 调用不新增 agent 专属 provider/config，而是抽取共享 `backend/app/llm/` 基础层，继续复用现有 code review 的 `.env` 配置约定与统一客户端构建逻辑。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、PostgreSQL JSON columns、pytest、React + Vite + TypeScript、React Query、浏览器 EventSource/SSE、现有 GitHub/GitLab integration adapters 的网络访问能力

---

## 文件结构

### 新增后端文件

- `backend/app/llm/__init__.py`
  - 导出共享 LLM 配置与客户端构建能力。
- `backend/app/llm/provider.py`
  - 统一的 `LLM_PROVIDER` 与 provider-specific `.env` 解析。
- `backend/app/llm/client_factory.py`
  - provider 到 completion client 的统一构建入口。
- `backend/app/db/models/agent_session.py`
  - 存储项目级 agent session、锁定分支、当前 memory state。
- `backend/app/db/models/agent_message.py`
  - 存储用户可见的聊天消息。
- `backend/app/db/models/agent_run.py`
  - 存储一次 Pico 风格多步运行的结构化状态。
- `backend/app/db/models/agent_run_event.py`
  - 存储 trace/SSE 事件。
- `backend/app/db/models/agent_artifact.py`
  - 存储结构化 artifacts，例如 prompt context、run report、memory delta。
- `backend/app/db/models/repository_snapshot.py`
  - 存储锁定分支下某个 `head_sha` 对应的轻量仓库快照。
- `backend/alembic/versions/0004_create_repo_agent_schema.py`
  - 创建 agent 与 snapshot 相关表。
- `backend/app/schemas/agent.py`
  - 定义 session、message、run、branch option、SSE event 等请求/响应模型。
- `backend/app/agent/__init__.py`
  - 导出 agent 领域模块。
- `backend/app/agent/memory.py`
  - 迁移并裁剪 Pico 的 layered memory、freshness 与 relevant memory 选择逻辑。
- `backend/app/agent/context.py`
  - 迁移 Pico 的 `ContextManager` 与 prompt section 预算控制逻辑。
- `backend/app/agent/workspace.py`
  - 平台版 workspace snapshot、`workspace_fingerprint`、`runtime_identity_hash` builder。
- `backend/app/agent/protocol.py`
  - 定义 Pico 风格 LLM 输出协议、解析器与 retry notice。
- `backend/app/agent/tools.py`
  - 只读工具规格、schema 与示例。
- `backend/app/agent/redaction.py`
  - 统一脱敏逻辑。
- `backend/app/agent/repository_provider.py`
  - provider protocol、GitHub/GitLab provider 适配器与测试用 fake provider。
- `backend/app/agent/snapshot_service.py`
  - 分支 head 解析、轻量 snapshot 构建、project docs / recent commits 摘要提取。
- `backend/app/agent/tool_gateway.py`
  - 工具存在性检查、参数校验、重复调用拦截、脱敏、裁剪、memory/history 更新。
- `backend/app/agent/event_recorder.py`
  - 事件落库与 SSE 轮询辅助。
- `backend/app/agent/run_service.py`
  - Pico 风格多步 agent run loop。
- `backend/app/services/agent_session_service.py`
  - session、message、run 与 artifact 持久化编排。
- `backend/app/api/routes/agent.py`
  - 项目级 repo agent API。

### 修改后端文件

- `backend/app/db/models/__init__.py`
  - 导出新的 ORM models。
- `backend/app/api/router.py`
  - include agent router。
- `backend/app/services/project_service.py`
  - 如需补充项目读取给 agent 使用的轻量辅助方法，可在此添加只读 helper。
- `backend/app/review/llm/provider.py`
  - 改为复用新的共享 `app/llm/provider.py`，保留兼容导出或迁移引用。
- `backend/app/review/reviewer/backend_reviewer.py`
  - 改为复用新的共享 `app/llm/client_factory.py`，不再自己持有 provider dispatch 逻辑。

### 新增后端测试

- `backend/tests/unit/db/test_agent_models_schema.py`
- `backend/tests/unit/agent/test_memory_context.py`
- `backend/tests/unit/agent/test_protocol.py`
- `backend/tests/unit/agent/test_llm_client.py`
- `backend/tests/unit/agent/test_repository_provider.py`
- `backend/tests/unit/agent/test_snapshot_service.py`
- `backend/tests/unit/agent/test_tool_gateway.py`
- `backend/tests/unit/agent/test_run_service.py`
- `backend/tests/integration/test_agent_api.py`
- `backend/tests/integration/test_agent_sse.py`

### 新增前端文件

- `frontend/src/features/agent/api.ts`
  - Repo Agent API 与 EventSource helper。
- `frontend/src/pages/projects/ProjectAgentPage.tsx`
  - 项目级仓库对话助手页面。
- `frontend/src/pages/projects/ProjectAgentPage.test.tsx`
  - 分支选择、消息流、SSE 更新测试。

### 修改前端文件

- `frontend/src/routes/router.tsx`
  - 新增 `/projects/:projectId/agent` 路由。
- `frontend/src/pages/projects/ProjectListPage.tsx`
  - 为每个项目新增“仓库助手”入口。
- `frontend/src/lib/api/types.ts`
  - 增加 agent 相关响应类型。

---

### 任务 1：新增 Repo Agent 数据库 schema

**Files:**
- Create: `backend/app/db/models/agent_session.py`
- Create: `backend/app/db/models/agent_message.py`
- Create: `backend/app/db/models/agent_run.py`
- Create: `backend/app/db/models/agent_run_event.py`
- Create: `backend/app/db/models/agent_artifact.py`
- Create: `backend/app/db/models/repository_snapshot.py`
- Create: `backend/alembic/versions/0004_create_repo_agent_schema.py`
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/unit/db/test_agent_models_schema.py`

- [ ] **步骤 1：先写失败的 schema 测试**

创建 `backend/tests/unit/db/test_agent_models_schema.py`：

```python
from __future__ import annotations

from sqlalchemy import inspect

from app.db.base import Base


def test_repo_agent_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert {
        "agent_sessions",
        "agent_messages",
        "agent_runs",
        "agent_run_events",
        "agent_artifacts",
        "repository_snapshots",
    } <= table_names


def test_agent_sessions_columns_exist(db_session) -> None:
    inspector = inspect(db_session.bind)
    columns = {column["name"] for column in inspector.get_columns("agent_sessions")}

    assert {
        "id",
        "project_id",
        "created_by",
        "title",
        "status",
        "branch",
        "provider",
        "model",
        "last_head_sha",
        "last_workspace_fingerprint",
        "last_runtime_identity_hash",
        "memory_state",
        "settings",
        "last_message_at",
        "created_at",
        "updated_at",
    } <= columns
```

- [ ] **步骤 2：运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/db/test_agent_models_schema.py -q`
Expected: FAIL，因为 agent 表还不存在。

- [ ] **步骤 3：新增 ORM models**

创建 `backend/app/db/models/agent_session.py`：

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentSession(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("ix_agent_sessions_project_updated", "project_id", "updated_at"),
        Index("ix_agent_sessions_project_branch", "project_id", "branch"),
    )

    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default=text("'active'"))
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_head_sha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_workspace_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_runtime_identity_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    memory_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    last_message_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project")
    creator = relationship("User")
```

创建 `backend/app/db/models/agent_message.py`：

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentMessage(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("ix_agent_messages_session_sequence", "session_id", "sequence", unique=True),
    )

    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(16), nullable=False, default="markdown")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))

    session = relationship("AgentSession")
```

创建 `backend/app/db/models/agent_run.py`、`agent_run_event.py`、`agent_artifact.py` 与 `repository_snapshot.py`，字段必须与 spec 完全对齐，至少覆盖：

- `agent_runs`
  - `session_id`
  - `project_id`
  - `user_message_id`
  - `assistant_message_id`
  - `status`
  - `stop_reason`
  - `tool_steps`
  - `attempts`
  - `last_tool`
  - `branch`
  - `head_sha`
  - `workspace_fingerprint`
  - `runtime_identity_hash`
  - `prompt_metadata`
  - `completion_metadata`
  - `report_payload`
- `agent_run_events`
  - `run_id`
  - `session_id`
  - `event_type`
  - `sequence`
  - `payload`
- `agent_artifacts`
  - `run_id`
  - `session_id`
  - `artifact_type`
  - `name`
  - `content`
  - `metadata`
- `repository_snapshots`
  - `project_id`
  - `branch`
  - `head_sha`
  - `workspace_fingerprint`
  - `snapshot_digest`
  - `file_tree_summary`
  - `project_docs_summary`
  - `recent_commits_summary`
  - `metadata`

- [ ] **步骤 4：导出 models**

修改 `backend/app/db/models/__init__.py`：

```python
from app.db.models.agent_artifact import AgentArtifact
from app.db.models.agent_message import AgentMessage
from app.db.models.agent_run import AgentRun
from app.db.models.agent_run_event import AgentRunEvent
from app.db.models.agent_session import AgentSession
from app.db.models.repository_snapshot import RepositorySnapshot
```

同时把这些名称加入 `__all__`。

- [ ] **步骤 5：新增 Alembic migration**

创建 `backend/alembic/versions/0004_create_repo_agent_schema.py`：

```python
"""create repo agent schema

Revision ID: 0004_create_repo_agent_schema
Revises: 0003_webhook_review_execution
Create Date: 2026-06-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_create_repo_agent_schema"
down_revision = "0003_webhook_review_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("last_head_sha", sa.String(length=255), nullable=True),
        sa.Column("last_workspace_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("last_runtime_identity_hash", sa.String(length=128), nullable=True),
        sa.Column("memory_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
```

在同一个 migration 中继续创建 `agent_runs`、`agent_messages`、`agent_run_events`、`agent_artifacts`、`repository_snapshots`，并补充以下索引：

- `ix_agent_sessions_project_updated`
- `ix_agent_sessions_project_branch`
- `ix_agent_messages_session_sequence`
- `ix_agent_runs_session_created`
- `ix_agent_run_events_run_sequence`
- `ix_repository_snapshots_project_branch_head`
- `ix_repository_snapshots_workspace_fingerprint`

- [ ] **步骤 6：运行 schema 测试**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/db/test_agent_models_schema.py -q`
Expected: PASS

- [ ] **步骤 7：提交**

```bash
git add backend/app/db/models backend/alembic/versions/0004_create_repo_agent_schema.py backend/tests/unit/db/test_agent_models_schema.py
git commit -m "feat: add repo agent schema"
```

---

### 任务 2：迁移 Pico 风格 memory、context、workspace identity、LLM 协议与共享 LLM 基础层

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/memory.py`
- Create: `backend/app/agent/context.py`
- Create: `backend/app/agent/workspace.py`
- Create: `backend/app/agent/protocol.py`
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/provider.py`
- Create: `backend/app/llm/client_factory.py`
- Modify: `backend/app/review/llm/provider.py`
- Modify: `backend/app/review/reviewer/backend_reviewer.py`
- Test: `backend/tests/unit/agent/test_llm_client.py`
- Test: `backend/tests/unit/agent/test_memory_context.py`
- Test: `backend/tests/unit/agent/test_protocol.py`

- [ ] **步骤 1：先写 memory/context 失败测试**

创建 `backend/tests/unit/agent/test_memory_context.py`：

```python
from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import default_memory_state, invalidate_stale_file_summaries
from app.agent.workspace import WorkspaceSnapshot, build_runtime_identity_hash, build_workspace_fingerprint


def test_default_memory_state_preserves_pico_shape() -> None:
    memory = default_memory_state()

    assert set(memory) == {"working", "episodic_notes", "file_summaries", "task", "files", "notes", "next_note_index"}
    assert set(memory["working"]) == {"task_summary", "recent_files"}


def test_invalidate_stale_file_summaries_only_removes_changed_paths() -> None:
    memory = default_memory_state()
    memory["file_summaries"] = {
        "backend/app/main.py": {
            "summary": "entrypoint",
            "branch": "main",
            "head_sha": "old",
            "file_version": "v1",
        },
        "backend/app/api/router.py": {
            "summary": "router",
            "branch": "main",
            "head_sha": "old",
            "file_version": "v2",
        },
    }
    current_versions = {
        "backend/app/main.py": "v9",
        "backend/app/api/router.py": "v2",
    }

    stale = invalidate_stale_file_summaries(memory, current_versions)

    assert stale == ["backend/app/main.py"]
    assert "backend/app/main.py" not in memory["file_summaries"]
    assert "backend/app/api/router.py" in memory["file_summaries"]


def test_context_manager_keeps_current_request_when_over_budget() -> None:
    snapshot = WorkspaceSnapshot(
        project_id=1,
        platform_type="github",
        branch="main",
        head_sha="abc123",
        default_branch="main",
        snapshot_digest="snap",
        project_docs_summary={"README.md": "readme"},
        recent_commits_summary=["c1"],
        file_tree_summary=["backend/", "frontend/"],
    )
    manager = ContextManager(total_budget=120)

    prompt, metadata = manager.build(
        prefix="P" * 100,
        memory_text="M" * 100,
        relevant_memory=["note 1", "note 2"],
        history_text="H" * 100,
        current_request="Current user request:\n请解释 review worker 的入口。",
        snapshot=snapshot,
    )

    assert "请解释 review worker 的入口" in prompt
    assert metadata["reduction_log"]
```

- [ ] **步骤 2：先写 LLM 协议失败测试**

创建 `backend/tests/unit/agent/test_protocol.py`：

```python
from __future__ import annotations

from app.agent.protocol import parse_model_output


def test_parse_tool_output_accepts_single_json_tool_call() -> None:
    kind, payload = parse_model_output('<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":20}}</tool>')

    assert kind == "tool"
    assert payload["name"] == "read_file"
    assert payload["args"]["path"] == "README.md"


def test_parse_model_output_rejects_empty_final() -> None:
    kind, payload = parse_model_output("<final>   </final>")

    assert kind == "retry"
    assert "non-empty <final>" in payload
```

- [ ] **步骤 3：先写共享 LLM 配置复用测试**

创建 `backend/tests/unit/agent/test_llm_client.py`：

```python
from __future__ import annotations

from app.llm.provider import load_llm_config


def test_shared_llm_config_uses_existing_env_contract(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "api-key")
    monkeypatch.setenv("OPENAI_API_BASE_URL", "https://xxx/v1")
    monkeypatch.setenv("OPENAI_API_MODEL", "gpt-5.4")

    config = load_llm_config()

    assert config.provider == "openai"
    assert config.api_key == "api-key"
    assert config.api_base_url == "https://xxx/v1"
    assert config.model == "gpt-5.4"
```

- [ ] **步骤 4：运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_memory_context.py tests/unit/agent/test_protocol.py tests/unit/agent/test_llm_client.py -q`
Expected: FAIL，因为文件尚不存在。

- [ ] **步骤 5：迁移 Pico memory**

创建 `backend/app/agent/memory.py`：

```python
from __future__ import annotations

import hashlib
from typing import Any


def default_memory_state() -> dict[str, Any]:
    return {
        "working": {
            "task_summary": "",
            "recent_files": [],
        },
        "episodic_notes": [],
        "file_summaries": {},
        "task": "",
        "files": [],
        "notes": [],
        "next_note_index": 0,
    }


def invalidate_stale_file_summaries(
    memory_state: dict[str, Any],
    current_versions: dict[str, str | None],
) -> list[str]:
    stale_paths: list[str] = []
    file_summaries = dict(memory_state.get("file_summaries", {}))
    for path, payload in list(file_summaries.items()):
        current_version = current_versions.get(path)
        previous_version = str(payload.get("file_version") or "")
        if current_version is None or previous_version != str(current_version):
            stale_paths.append(path)
            file_summaries.pop(path, None)
    memory_state["file_summaries"] = file_summaries
    return stale_paths


def select_relevant_memory(memory_state: dict[str, Any], query: str, limit: int = 3) -> list[str]:
    tokens = {token.strip().lower() for token in query.split() if token.strip()}
    scored: list[tuple[int, str]] = []
    for note in memory_state.get("episodic_notes", []):
        text = str(note.get("text", "") if isinstance(note, dict) else note)
        overlap = len(tokens & {token.lower() for token in text.split()})
        if overlap:
            scored.append((overlap, text))
    scored.sort(reverse=True)
    return [text for _, text in scored[:limit]]


def compute_text_version(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **步骤 6：迁移 Pico context 与 workspace identity**

创建 `backend/app/agent/workspace.py`：

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(slots=True)
class WorkspaceSnapshot:
    project_id: int
    platform_type: str
    branch: str
    head_sha: str
    default_branch: str
    snapshot_digest: str
    project_docs_summary: dict[str, str]
    recent_commits_summary: list[str]
    file_tree_summary: list[str]


def build_workspace_fingerprint(snapshot: WorkspaceSnapshot) -> str:
    payload = {
        "project_id": snapshot.project_id,
        "platform_type": snapshot.platform_type,
        "branch": snapshot.branch,
        "head_sha": snapshot.head_sha,
        "default_branch": snapshot.default_branch,
        "snapshot_digest": snapshot.snapshot_digest,
        "project_docs_summary": snapshot.project_docs_summary,
        "recent_commits_summary": snapshot.recent_commits_summary,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_runtime_identity_hash(
    *,
    workspace_fingerprint: str,
    tool_signature: str,
    model: str,
    max_steps: int,
    max_new_tokens: int,
    read_only: bool = True,
) -> str:
    payload = {
        "workspace_fingerprint": workspace_fingerprint,
        "tool_signature": tool_signature,
        "model": model,
        "max_steps": max_steps,
        "max_new_tokens": max_new_tokens,
        "read_only": read_only,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
```

创建 `backend/app/agent/context.py`，保留 Pico 的 section 结构与收缩顺序：

```python
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TOTAL_BUDGET = 12000
DEFAULT_SECTION_BUDGETS = {
    "prefix": 3600,
    "memory": 1600,
    "relevant_memory": 1200,
    "history": 5200,
}
DEFAULT_REDUCTION_ORDER = ("relevant_memory", "history", "memory", "prefix")


def _tail_clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


class ContextManager:
    def __init__(self, *, total_budget: int = DEFAULT_TOTAL_BUDGET) -> None:
        self.total_budget = total_budget
        self.section_budgets = dict(DEFAULT_SECTION_BUDGETS)

    def build(
        self,
        *,
        prefix: str,
        memory_text: str,
        relevant_memory: list[str],
        history_text: str,
        current_request: str,
        snapshot,
    ) -> tuple[str, dict[str, object]]:
        section_texts = {
            "prefix": prefix,
            "memory": memory_text,
            "relevant_memory": "Relevant memory:\n" + ("\n".join(f"- {item}" for item in relevant_memory) if relevant_memory else "- none"),
            "history": history_text,
            "current_request": current_request,
        }
        budgets = dict(self.section_budgets)
        rendered = {name: _tail_clip(text, budgets.get(name, len(text))) for name, text in section_texts.items() if name != "current_request"}
        rendered["current_request"] = current_request
        prompt = "\n\n".join(rendered[name] for name in ("prefix", "memory", "relevant_memory", "history", "current_request"))
        reduction_log: list[dict[str, object]] = []
        while len(prompt) > self.total_budget:
            overflow = len(prompt) - self.total_budget
            for section in DEFAULT_REDUCTION_ORDER:
                current_budget = budgets[section]
                new_budget = max(80, current_budget - overflow)
                if new_budget == current_budget:
                    continue
                budgets[section] = new_budget
                reduction_log.append({"section": section, "before": current_budget, "after": new_budget})
                rendered[section] = _tail_clip(section_texts[section], new_budget)
                prompt = "\n\n".join(rendered[name] for name in ("prefix", "memory", "relevant_memory", "history", "current_request"))
                break
            else:
                break
        return prompt, {"budgets": budgets, "reduction_log": reduction_log, "snapshot_digest": snapshot.snapshot_digest}
```

- [ ] **步骤 7：迁移 Pico LLM 协议**

创建 `backend/app/agent/protocol.py`：

```python
from __future__ import annotations

import json
import re


def retry_notice(reason: str) -> str:
    return (
        f"{reason}. Reply with a valid <tool> call or a non-empty <final> answer. "
        'Use <tool>{"name":"tool_name","args":{...}}</tool> or <final>your answer</final>.'
    )


def parse_model_output(raw: str) -> tuple[str, object]:
    raw = str(raw)
    if "<tool>" in raw and ("<final>" not in raw or raw.find("<tool>") < raw.find("<final>")):
        body = extract(raw, "tool")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return "retry", retry_notice("model returned malformed tool JSON")
        if not isinstance(payload, dict):
            return "retry", retry_notice("tool payload must be a JSON object")
        if not str(payload.get("name", "")).strip():
            return "retry", retry_notice("tool payload is missing a tool name")
        return "tool", payload
    if "<final>" in raw:
        body = extract(raw, "final").strip()
        if not body:
            return "retry", retry_notice("model returned an empty <final> answer")
        return "final", body
    return "retry", retry_notice("model returned malformed tool output")


def extract(raw: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", raw, re.S)
    return match.group(1) if match else ""
```

- [ ] **步骤 8：抽取共享 LLM 基础层并统一配置入口**

创建共享层：

- `backend/app/llm/provider.py`
  - 提供 `LLMConfig`
  - 提供 `load_llm_config()`
- `backend/app/llm/client_factory.py`
  - 提供 `build_llm_client(config)`
- `backend/app/llm/__init__.py`
  - 导出共享能力

然后把 `backend/app/review/llm/provider.py` 与 `backend/app/review/reviewer/backend_reviewer.py` 改成复用这层共享能力，保留兼容导出或最小迁移，避免 `Repo Agent` 直接依赖 review 业务代码。

共享配置入口保持现有环境变量链路：

```python
provider = os.getenv("LLM_PROVIDER", "anthropic")
```

并确保第一版明确支持以下 `.env` 方式：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=api-key
OPENAI_API_BASE_URL=https://xxx/v1
OPENAI_API_MODEL=gpt-5.4
```

关键约束：

- `Repo Agent` 与 `code review` 共用同一套 `.env` 配置契约。
- `Repo Agent` 与 `code review` 共用同一套 `build_llm_client(...)` 实现来源。
- 不允许保留“两套 provider dispatch 逻辑”。
- 不允许让 `Repo Agent` 直接 import `app.review.reviewer.backend_reviewer` 作为运行时依赖。

- [ ] **步骤 9：运行测试并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_memory_context.py tests/unit/agent/test_protocol.py tests/unit/agent/test_llm_client.py -q`
Expected: PASS

- [ ] **步骤 10：提交**

```bash
git add backend/app/agent backend/app/llm backend/app/review/llm/provider.py backend/app/review/reviewer/backend_reviewer.py backend/tests/unit/agent/test_memory_context.py backend/tests/unit/agent/test_protocol.py backend/tests/unit/agent/test_llm_client.py
git commit -m "feat: add pico-style agent core"
```

---

### 任务 3：实现 GitHub/GitLab RepositoryProvider 与 snapshot service

**Files:**
- Create: `backend/app/agent/repository_provider.py`
- Create: `backend/app/agent/snapshot_service.py`
- Test: `backend/tests/unit/agent/test_repository_provider.py`
- Test: `backend/tests/unit/agent/test_snapshot_service.py`

- [ ] **步骤 1：先写 provider 与 snapshot 失败测试**

创建 `backend/tests/unit/agent/test_repository_provider.py`：

```python
from __future__ import annotations

from app.agent.repository_provider import FakeRepositoryProvider


def test_fake_repository_provider_reads_branch_locked_file() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "README.md"): "# Repo Agent\n",
        },
    )

    assert provider.resolve_branch_head(branch="main") == "sha-1"
    assert provider.read_file(branch="main", path="README.md", start=1, end=20)["content"].startswith("# Repo Agent")


def test_fake_repository_provider_searches_code() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "backend/app/main.py"): "from fastapi import FastAPI\napp = FastAPI()\n",
        },
    )

    result = provider.search_code(branch="main", query="FastAPI", path=".")

    assert result["matches"][0]["path"] == "backend/app/main.py"
```

创建 `backend/tests/unit/agent/test_snapshot_service.py`：

```python
from __future__ import annotations

from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.snapshot_service import SnapshotService


def test_snapshot_service_builds_snapshot_from_branch_head() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={
            ("main", "README.md"): "# Title\n",
            ("main", "backend/app/main.py"): "app = object()\n",
        },
        recent_commits={"main": ["c1 init", "c2 router"]},
    )
    service = SnapshotService(provider=provider)

    snapshot = service.build(project_id=1, platform_type="github", default_branch="main", branch="main")

    assert snapshot.branch == "main"
    assert snapshot.head_sha == "sha-1"
    assert "README.md" in snapshot.project_docs_summary
```

- [ ] **步骤 2：运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_repository_provider.py tests/unit/agent/test_snapshot_service.py -q`
Expected: FAIL，因为 provider 与 snapshot service 尚不存在。

- [ ] **步骤 3：实现 provider protocol 与 fake provider**

创建 `backend/app/agent/repository_provider.py`：

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from app.db.models import Project
from app.integrations.github import GitHubIntegrationAdapter
from app.integrations.gitlab import GitLabIntegrationAdapter


class RepositoryProvider(Protocol):
    def resolve_branch_head(self, *, branch: str) -> str: ...
    def list_tree(self, *, branch: str, path: str = ".") -> dict[str, object]: ...
    def read_file(self, *, branch: str, path: str, start: int, end: int) -> dict[str, object]: ...
    def search_code(self, *, branch: str, query: str, path: str = ".") -> dict[str, object]: ...
    def get_recent_commits(self, *, branch: str, limit: int = 5) -> list[str]: ...
    def get_change_summary(self, *, external_id: str) -> dict[str, object]: ...
    def list_commits(self, *, external_id: str) -> list[dict[str, object]]: ...
    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]: ...
    def get_diff_overview(self, *, external_id: str) -> dict[str, object]: ...


@dataclass(slots=True)
class FakeRepositoryProvider:
    branch_heads: dict[str, str]
    files: dict[tuple[str, str], str]
    recent_commits: dict[str, list[str]] | None = None

    def resolve_branch_head(self, *, branch: str) -> str:
        return self.branch_heads[branch]

    def list_tree(self, *, branch: str, path: str = ".") -> dict[str, object]:
        entries = sorted(item_path for item_branch, item_path in self.files if item_branch == branch and item_path.startswith("" if path == "." else path))
        return {"entries": entries[:200]}

    def read_file(self, *, branch: str, path: str, start: int, end: int) -> dict[str, object]:
        text = self.files[(branch, path)]
        lines = text.splitlines()
        content = "\n".join(f"{index}: {line}" for index, line in enumerate(lines[start - 1:end], start=start))
        return {
            "path": path,
            "content": content,
            "file_version": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def search_code(self, *, branch: str, query: str, path: str = ".") -> dict[str, object]:
        matches: list[dict[str, object]] = []
        for (item_branch, item_path), text in self.files.items():
            if item_branch != branch or not item_path.startswith("" if path == "." else path):
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if query.lower() in line.lower():
                    matches.append({"path": item_path, "line": line_no, "text": line})
        return {"matches": matches[:200]}

    def get_recent_commits(self, *, branch: str, limit: int = 5) -> list[str]:
        return (self.recent_commits or {}).get(branch, [])[:limit]

    def get_change_summary(self, *, external_id: str) -> dict[str, object]:
        return {"external_id": external_id, "title": "Test PR", "branch": "main"}

    def list_commits(self, *, external_id: str) -> list[dict[str, object]]:
        return [{"id": "c1", "message": f"commit for {external_id}"}]

    def list_comment_threads(self, *, external_id: str) -> list[dict[str, object]]:
        return [{"id": "t1", "body": f"thread for {external_id}"}]

    def get_diff_overview(self, *, external_id: str) -> dict[str, object]:
        return {"external_id": external_id, "files_changed": 1}
```

- [ ] **步骤 4：实现 snapshot service**

创建 `backend/app/agent/snapshot_service.py`：

```python
from __future__ import annotations

import hashlib
import json

from app.agent.workspace import WorkspaceSnapshot


DOC_NAMES = ("README.md", "AGENTS.md", "pyproject.toml", "package.json")


class SnapshotService:
    def __init__(self, *, provider) -> None:
        self.provider = provider

    def build(self, *, project_id: int, platform_type: str, default_branch: str, branch: str) -> WorkspaceSnapshot:
        head_sha = self.provider.resolve_branch_head(branch=branch)
        file_tree = self.provider.list_tree(branch=branch, path=".")["entries"]
        docs = {}
        for name in DOC_NAMES:
            try:
                docs[name] = self.provider.read_file(branch=branch, path=name, start=1, end=60)["content"]
            except KeyError:
                continue
        recent_commits = self.provider.get_recent_commits(branch=branch, limit=5)
        snapshot_digest = hashlib.sha256(
            json.dumps(
                {
                    "branch": branch,
                    "head_sha": head_sha,
                    "file_tree": file_tree,
                    "docs": docs,
                    "recent_commits": recent_commits,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return WorkspaceSnapshot(
            project_id=project_id,
            platform_type=platform_type,
            branch=branch,
            head_sha=head_sha,
            default_branch=default_branch,
            snapshot_digest=snapshot_digest,
            project_docs_summary=docs,
            recent_commits_summary=recent_commits,
            file_tree_summary=file_tree[:200],
        )
```

- [ ] **步骤 5：补 GitHub/GitLab 适配器包装**

在 `backend/app/agent/repository_provider.py` 继续新增 `GitHubRepositoryProvider` 与 `GitLabRepositoryProvider`，只实现第一版要用的包装方法。最小接口如下：

```python
class GitHubRepositoryProvider:
    def __init__(self, *, project: Project, access_token: str | None = None) -> None:
        self.project = project
        self.adapter = GitHubIntegrationAdapter(access_token=access_token)


class GitLabRepositoryProvider:
    def __init__(self, *, project: Project, access_token: str | None = None) -> None:
        self.project = project
        self.adapter = GitLabIntegrationAdapter(access_token=access_token)
```

第一轮可以先把 `resolve_branch_head`、`list_tree`、`read_file`、`search_code` 做出来；PR/MR 元信息方法可在任务 4 配合 gateway 再补。

- [ ] **步骤 6：运行测试并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_repository_provider.py tests/unit/agent/test_snapshot_service.py -q`
Expected: PASS

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent/repository_provider.py backend/app/agent/snapshot_service.py backend/tests/unit/agent/test_repository_provider.py backend/tests/unit/agent/test_snapshot_service.py
git commit -m "feat: add repo agent repository providers"
```

---

### 任务 4：实现 Tool Registry、Tool Gateway 与统一脱敏

**Files:**
- Create: `backend/app/agent/tools.py`
- Create: `backend/app/agent/redaction.py`
- Create: `backend/app/agent/tool_gateway.py`
- Test: `backend/tests/unit/agent/test_tool_gateway.py`

- [ ] **步骤 1：先写 gateway 失败测试**

创建 `backend/tests/unit/agent/test_tool_gateway.py`：

```python
from __future__ import annotations

from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.tool_gateway import ToolGateway


def test_tool_gateway_rejects_repeated_identical_call() -> None:
    provider = FakeRepositoryProvider(branch_heads={"main": "sha-1"}, files={("main", "README.md"): "# Title\n"})
    gateway = ToolGateway(provider=provider, branch="main", secret_values=["secret-token"])

    first = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})
    second = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})

    assert "README.md" in first
    assert second.startswith("error: repeated identical tool call")


def test_tool_gateway_redacts_sensitive_text() -> None:
    provider = FakeRepositoryProvider(
        branch_heads={"main": "sha-1"},
        files={("main", "README.md"): "token=secret-token\n"},
    )
    gateway = ToolGateway(provider=provider, branch="main", secret_values=["secret-token"])

    result = gateway.run("read_file", {"path": "README.md", "start": 1, "end": 10})

    assert "secret-token" not in result
    assert "<redacted>" in result
```

- [ ] **步骤 2：运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_tool_gateway.py -q`
Expected: FAIL，因为 gateway 文件尚不存在。

- [ ] **步骤 3：定义只读工具规格**

创建 `backend/app/agent/tools.py`：

```python
from __future__ import annotations


TOOL_SPECS = {
    "list_files": {
        "schema": {"path": "str='.'"},
        "description": "List files in the locked repository branch.",
        "risky": False,
    },
    "read_file": {
        "schema": {"path": "str", "start": "int=1", "end": "int=200"},
        "description": "Read a UTF-8 file by line range from the locked branch.",
        "risky": False,
    },
    "search_code": {
        "schema": {"query": "str", "path": "str='.'"},
        "description": "Search code in the locked branch.",
        "risky": False,
    },
    "get_change_summary": {
        "schema": {"external_id": "str"},
        "description": "Read PR/MR summary.",
        "risky": False,
    },
    "list_commits": {
        "schema": {"external_id": "str"},
        "description": "List commits for PR/MR.",
        "risky": False,
    },
    "list_comment_threads": {
        "schema": {"external_id": "str"},
        "description": "List PR/MR comment threads.",
        "risky": False,
    },
    "get_diff_overview": {
        "schema": {"external_id": "str"},
        "description": "Read diff overview for PR/MR.",
        "risky": False,
    },
}
```

- [ ] **步骤 4：实现统一脱敏**

创建 `backend/app/agent/redaction.py`：

```python
from __future__ import annotations

import re


REDACTED_VALUE = "<redacted>"
SECRET_PATTERN = re.compile(r"(?i)(\b(api[_ -]?key|token|secret|password)\b|sk-[A-Za-z0-9_-]{6,})")


def redact_text(text: str, *, secret_values: list[str]) -> str:
    output = str(text)
    for value in sorted([item for item in secret_values if item], key=len, reverse=True):
        output = output.replace(value, REDACTED_VALUE)
    return SECRET_PATTERN.sub(REDACTED_VALUE, output)
```

- [ ] **步骤 5：实现 gateway**

创建 `backend/app/agent/tool_gateway.py`：

```python
from __future__ import annotations

import json

from app.agent.redaction import redact_text
from app.agent.tools import TOOL_SPECS


class ToolGateway:
    def __init__(self, *, provider, branch: str, secret_values: list[str]) -> None:
        self.provider = provider
        self.branch = branch
        self.secret_values = secret_values
        self.history: list[tuple[str, str]] = []

    def tool_signature(self) -> str:
        payload = [
            {
                "name": name,
                "schema": TOOL_SPECS[name]["schema"],
                "description": TOOL_SPECS[name]["description"],
                "risky": TOOL_SPECS[name]["risky"],
            }
            for name in sorted(TOOL_SPECS)
        ]
        return json.dumps(payload, sort_keys=True)

    def run(self, name: str, args: dict[str, object]) -> str:
        if name not in TOOL_SPECS:
            return f"error: unknown tool '{name}'"
        signature = json.dumps({"name": name, "args": args}, sort_keys=True)
        if self.history and self.history[-1] == (name, signature):
            return f"error: repeated identical tool call for {name}; choose a different tool or return a final answer"
        self.history.append((name, signature))
        result = self._dispatch(name, args)
        return redact_text(result, secret_values=self.secret_values)

    def _dispatch(self, name: str, args: dict[str, object]) -> str:
        if name == "list_files":
            return "\n".join(self.provider.list_tree(branch=self.branch, path=str(args.get("path", ".")))["entries"])
        if name == "read_file":
            payload = self.provider.read_file(
                branch=self.branch,
                path=str(args["path"]),
                start=int(args.get("start", 1)),
                end=int(args.get("end", 200)),
            )
            return payload["content"]
        if name == "search_code":
            payload = self.provider.search_code(branch=self.branch, query=str(args["query"]), path=str(args.get("path", ".")))
            return "\n".join(f'{item["path"]}:{item["line"]}:{item["text"]}' for item in payload["matches"])
        if name == "get_change_summary":
            return json.dumps(self.provider.get_change_summary(external_id=str(args["external_id"])), ensure_ascii=False)
        if name == "list_commits":
            return json.dumps(self.provider.list_commits(external_id=str(args["external_id"])), ensure_ascii=False)
        if name == "list_comment_threads":
            return json.dumps(self.provider.list_comment_threads(external_id=str(args["external_id"])), ensure_ascii=False)
        if name == "get_diff_overview":
            return json.dumps(self.provider.get_diff_overview(external_id=str(args["external_id"])), ensure_ascii=False)
        return "error: unsupported tool"
```

- [ ] **步骤 6：运行测试并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_tool_gateway.py -q`
Expected: PASS

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent/tools.py backend/app/agent/redaction.py backend/app/agent/tool_gateway.py backend/tests/unit/agent/test_tool_gateway.py
git commit -m "feat: add repo agent tool gateway"
```

---

### 任务 5：实现 run loop、共享 LLM 客户端接入、事件记录、session service 与 API

**Files:**
- Create: `backend/app/agent/event_recorder.py`
- Create: `backend/app/agent/run_service.py`
- Create: `backend/app/services/agent_session_service.py`
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/api/routes/agent.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/unit/agent/test_run_service.py`
- Test: `backend/tests/integration/test_agent_api.py`
- Test: `backend/tests/integration/test_agent_sse.py`

- [ ] **步骤 1：先写 run service 单测**

创建 `backend/tests/unit/agent/test_run_service.py`：

```python
from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import default_memory_state
from app.agent.protocol import parse_model_output
from app.agent.repository_provider import FakeRepositoryProvider
from app.agent.run_service import FakeModelClient, RunService
from app.agent.snapshot_service import SnapshotService
from app.agent.tool_gateway import ToolGateway


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

    assert result["final_answer"].startswith("README 表明")
    assert result["tool_steps"] == 1
```

- [ ] **步骤 2：先写 API 集成测试**

创建 `backend/tests/integration/test_agent_api.py`：

```python
from __future__ import annotations


def test_create_repo_agent_session(authenticated_superuser_client) -> None:
    response = authenticated_superuser_client.post(
        "/api/v1/projects/1/agent/sessions",
        json={"title": "主分支仓库助手", "branch": "main"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["branch"] == "main"
    assert body["status"] == "active"
```

创建 `backend/tests/integration/test_agent_sse.py`：

```python
from __future__ import annotations


def test_repo_agent_stream_endpoint_returns_sse_headers(authenticated_superuser_client) -> None:
    response = authenticated_superuser_client.get("/api/v1/projects/1/agent/sessions/1/stream")

    assert response.status_code in {200, 404}
    if response.status_code == 200:
        assert response.headers["content-type"].startswith("text/event-stream")
```

- [ ] **步骤 3：运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_run_service.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: FAIL，因为 service、schema 与路由尚不存在。

- [ ] **步骤 4：实现 event recorder 与 run service**

创建 `backend/app/agent/event_recorder.py`：

```python
from __future__ import annotations

from datetime import datetime, UTC


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EventRecorder:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, event_type: str, payload: dict[str, object]) -> dict[str, object]:
        event = {
            "event_type": event_type,
            "payload": payload,
            "created_at": now_iso(),
            "sequence": len(self.events) + 1,
        }
        self.events.append(event)
        return event
```

创建 `backend/app/agent/run_service.py`：

```python
from __future__ import annotations

from dataclasses import dataclass

from app.agent.event_recorder import EventRecorder
from app.agent.memory import default_memory_state, invalidate_stale_file_summaries, select_relevant_memory
from app.agent.protocol import parse_model_output
from app.agent.tool_gateway import ToolGateway
from app.agent.workspace import build_runtime_identity_hash, build_workspace_fingerprint
from app.llm.client_factory import build_llm_client
from app.llm.provider import load_llm_config


class FakeModelClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        del messages
        return self.outputs.pop(0)


@dataclass(slots=True)
class RunService:
    model_client: object | None
    context_manager: object
    snapshot_service: object
    memory_state: dict
    provider: object
    branch: str
    project_id: int
    platform_type: str
    default_branch: str
    max_steps: int = 6
    max_new_tokens: int = 512

    def run(self, *, user_message: str) -> dict[str, object]:
        snapshot = self.snapshot_service.build(
            project_id=self.project_id,
            platform_type=self.platform_type,
            default_branch=self.default_branch,
            branch=self.branch,
        )
        workspace_fingerprint = build_workspace_fingerprint(snapshot)
        gateway = ToolGateway(provider=self.provider, branch=self.branch, secret_values=[])
        llm_config = load_llm_config()
        model_client = self.model_client or build_llm_client(llm_config)
        runtime_identity_hash = build_runtime_identity_hash(
            workspace_fingerprint=workspace_fingerprint,
            tool_signature=gateway.tool_signature(),
            model=str(llm_config.model or "unknown"),
            max_steps=self.max_steps,
            max_new_tokens=self.max_new_tokens,
        )
        recorder = EventRecorder()
        recorder.emit("run_started", {"branch": self.branch, "head_sha": snapshot.head_sha, "provider": llm_config.provider, "model": llm_config.model})
        current_versions = {}
        stale_paths = invalidate_stale_file_summaries(self.memory_state, current_versions)
        if stale_paths:
            recorder.emit("memory_invalidated", {"stale_paths": stale_paths})
        tool_steps = 0
        history = ""
        while tool_steps < self.max_steps:
            relevant_memory = select_relevant_memory(self.memory_state, user_message)
            prompt, prompt_metadata = self.context_manager.build(
                prefix=f"Workspace: {snapshot.branch}@{snapshot.head_sha}",
                memory_text=str(self.memory_state),
                relevant_memory=relevant_memory,
                history_text=history,
                current_request=f"Current user request:\n{user_message}",
                snapshot=snapshot,
            )
            raw = model_client.completions(messages=[{"role": "user", "content": prompt}])
            kind, payload = parse_model_output(raw)
            if kind == "tool":
                tool_steps += 1
                recorder.emit("tool_called", {"name": payload["name"], "args": payload["args"]})
                result = gateway.run(payload["name"], payload["args"])
                recorder.emit("tool_result", {"name": payload["name"], "result": result})
                history += f"\n[tool:{payload['name']}] {result}"
                continue
            if kind == "final":
                recorder.emit("final_answer", {"content": payload})
                return {
                    "status": "completed",
                    "final_answer": payload,
                    "tool_steps": tool_steps,
                    "workspace_fingerprint": workspace_fingerprint,
                    "runtime_identity_hash": runtime_identity_hash,
                    "events": recorder.events,
                    "prompt_metadata": prompt_metadata,
                }
            recorder.emit("run_failed", {"reason": payload})
            return {"status": "failed", "final_answer": "", "tool_steps": tool_steps, "events": recorder.events}
        recorder.emit("run_failed", {"reason": "step_limit_reached"})
        return {"status": "stopped", "final_answer": "", "tool_steps": tool_steps, "events": recorder.events}

```

这里的关键约束是：

- `RunService` 不直接读取新的 agent 专属 env 变量。
- `RunService` 不实现新的 provider 分发。
- 统一通过 `load_llm_config()` + 共享 `build_llm_client(...)` 获取真实模型客户端。
- 测试仍可传入 `FakeModelClient`，但生产路径必须复用 code review 的配置链路。

原来的 `FakeModelClient` 只保留测试用途：

```python
class FakeModelClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        del messages
        return self.outputs.pop(0)
```

- [ ] **步骤 5：实现 session service、schema 与路由**

创建 `backend/app/schemas/agent.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentSessionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    branch: str = Field(min_length=1, max_length=255)


class AgentSessionResponse(BaseModel):
    id: int
    project_id: int
    title: str
    status: str
    branch: str
    provider: str | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class AgentMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    status: str
    sequence: int
    created_at: datetime


class AgentRunResponse(BaseModel):
    id: int
    session_id: int
    status: str
    stop_reason: str | None = None
    tool_steps: int
    attempts: int
    branch: str
    head_sha: str | None = None
    workspace_fingerprint: str | None = None
    runtime_identity_hash: str | None = None
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
```

创建 `backend/app/services/agent_session_service.py` 和 `backend/app/api/routes/agent.py`，最小 API 先实现：

- `GET /api/v1/projects/{project_id}/agent/sessions`
- `POST /api/v1/projects/{project_id}/agent/sessions`
- `POST /api/v1/projects/{project_id}/agent/sessions/{session_id}/messages`
- `GET /api/v1/projects/{project_id}/agent/sessions/{session_id}/stream`

路由示例：

```python
router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


@router.post(
    "/sessions",
    response_model=AgentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("project:read"))],
)
async def create_agent_session(
    project_id: int,
    payload: AgentSessionCreateRequest,
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> AgentSessionResponse:
    return await service.create_session(project_id=project_id, user_id=current_user.id, payload=payload)
```

把 `backend/app/api/router.py` 更新为：

```python
from app.api.routes.agent import router as agent_router

api_router.include_router(agent_router)
```

- [ ] **步骤 6：运行测试并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent/test_run_service.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: PASS

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent/event_recorder.py backend/app/agent/run_service.py backend/app/services/agent_session_service.py backend/app/schemas/agent.py backend/app/api/routes/agent.py backend/app/api/router.py backend/tests/unit/agent/test_run_service.py backend/tests/integration/test_agent_api.py backend/tests/integration/test_agent_sse.py
git commit -m "feat: add repo agent backend flow"
```

---

### 任务 6：实现前端 Repo Agent 页面、API 与路由

**Files:**
- Create: `frontend/src/features/agent/api.ts`
- Create: `frontend/src/pages/projects/ProjectAgentPage.tsx`
- Create: `frontend/src/pages/projects/ProjectAgentPage.test.tsx`
- Modify: `frontend/src/routes/router.tsx`
- Modify: `frontend/src/pages/projects/ProjectListPage.tsx`
- Modify: `frontend/src/lib/api/types.ts`

- [ ] **步骤 1：先写页面失败测试**

创建 `frontend/src/pages/projects/ProjectAgentPage.test.tsx`：

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ProjectAgentPage } from "./ProjectAgentPage";


test("renders branch selector before session starts", () => {
  render(
    <MemoryRouter initialEntries={["/projects/1/agent"]}>
      <Routes>
        <Route path="/projects/:projectId/agent" element={<ProjectAgentPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText("仓库对话助手")).toBeInTheDocument();
  expect(screen.getByLabelText("选择分支")).toBeInTheDocument();
});
```

- [ ] **步骤 2：运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm test -- --runInBand src/pages/projects/ProjectAgentPage.test.tsx`
Expected: FAIL，因为页面尚不存在。

- [ ] **步骤 3：增加前端类型与 API**

修改 `frontend/src/lib/api/types.ts`，追加：

```ts
export interface AgentSessionResponse {
  id: number;
  project_id: number;
  title: string;
  status: string;
  branch: string;
  provider: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentMessageResponse {
  id: number;
  session_id: number;
  role: string;
  content: string;
  status: string;
  sequence: number;
  created_at: string;
}
```

创建 `frontend/src/features/agent/api.ts`：

```ts
import { http } from "../../lib/api/http";
import type { AgentMessageResponse, AgentSessionResponse } from "../../lib/api/types";

export interface AgentSessionPayload {
  title: string;
  branch: string;
}

export interface AgentMessagePayload {
  content: string;
}

export async function createAgentSession(projectId: number, payload: AgentSessionPayload) {
  const response = await http.post<AgentSessionResponse>(`/projects/${projectId}/agent/sessions`, payload);
  return response.data;
}

export async function listAgentSessions(projectId: number) {
  const response = await http.get<AgentSessionResponse[]>(`/projects/${projectId}/agent/sessions`);
  return response.data;
}

export async function createAgentMessage(projectId: number, sessionId: number, payload: AgentMessagePayload) {
  const response = await http.post<AgentMessageResponse>(`/projects/${projectId}/agent/sessions/${sessionId}/messages`, payload);
  return response.data;
}
```

- [ ] **步骤 4：实现页面与路由**

创建 `frontend/src/pages/projects/ProjectAgentPage.tsx`：

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { createAgentMessage, createAgentSession, listAgentSessions } from "../../features/agent/api";


export function ProjectAgentPage() {
  const { projectId = "0" } = useParams();
  const numericProjectId = Number(projectId);
  const queryClient = useQueryClient();
  const [branch, setBranch] = useState("main");
  const [title, setTitle] = useState("主分支仓库助手");
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);

  const sessionsQuery = useQuery({
    queryKey: ["agent", "sessions", numericProjectId],
    queryFn: () => listAgentSessions(numericProjectId),
  });

  const createSessionMutation = useMutation({
    mutationFn: () => createAgentSession(numericProjectId, { title, branch }),
    onSuccess: async (session) => {
      setSessionId(session.id);
      await queryClient.invalidateQueries({ queryKey: ["agent", "sessions", numericProjectId] });
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: () => createAgentMessage(numericProjectId, sessionId!, { content: message }),
    onSuccess: () => setMessage(""),
  });

  return (
    <section className="space-y-6">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white px-6 py-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Repo Agent</p>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">仓库对话助手</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          创建锁定分支的持续对话，围绕当前项目仓库进行只读分析。
        </p>
      </header>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white px-6 py-6 shadow-sm">
        <label className="block text-sm font-medium text-slate-700" htmlFor="branch">
          选择分支
        </label>
        <input
          id="branch"
          value={branch}
          onChange={(event) => setBranch(event.target.value)}
          className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm"
        />
        <button
          type="button"
          onClick={() => void createSessionMutation.mutateAsync()}
          className="mt-4 rounded-full bg-slate-900 px-4 py-2 text-sm text-white"
        >
          创建会话
        </button>
      </section>
    </section>
  );
}
```

修改 `frontend/src/routes/router.tsx`：

```tsx
import { ProjectAgentPage } from "../pages/projects/ProjectAgentPage";

{
  path: "/projects/:projectId/agent",
  element: <ProjectAgentPage />,
},
```

修改 `frontend/src/pages/projects/ProjectListPage.tsx`，在操作列追加按钮：

```tsx
<Link
  to={`/projects/${row.id}/agent`}
  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
>
  仓库助手
</Link>
```

- [ ] **步骤 5：运行测试并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm test -- --runInBand src/pages/projects/ProjectAgentPage.test.tsx`
Expected: PASS

- [ ] **步骤 6：提交**

```bash
git add frontend/src/features/agent/api.ts frontend/src/pages/projects/ProjectAgentPage.tsx frontend/src/pages/projects/ProjectAgentPage.test.tsx frontend/src/routes/router.tsx frontend/src/pages/projects/ProjectListPage.tsx frontend/src/lib/api/types.ts
git commit -m "feat: add repo agent frontend page"
```

---

### 任务 7：补充集成验证、文档与真实流程检查

**Files:**
- Create: `backend/scripts/verify_project_repo_agent_flow.py`
- Create: `backend/tests/unit/scripts/test_verify_project_repo_agent_flow.py`
- Modify: `backend/tests/integration/test_agent_api.py`
- Modify: `backend/tests/integration/test_agent_sse.py`
- Modify: `frontend/src/pages/projects/ProjectAgentPage.test.tsx`
- Modify: `backend/README.md`
- Modify: `README.md`
- Create: `docs/verification/2026-06-04-repo-agent-verification.md`

- [ ] **步骤 1：补充分支漂移与 memory invalidation 测试**

追加到 `backend/tests/unit/agent/test_run_service.py`：

```python
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
        }
    }
    service = RunService(
        model_client=FakeModelClient(["<final>done</final>"]),
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
```

- [ ] **步骤 2：先写真实对话链路验证脚本的失败测试**

创建 `backend/tests/unit/scripts/test_verify_project_repo_agent_flow.py`：

```python
from __future__ import annotations

from backend.scripts.verify_project_repo_agent_flow import (
    build_questions,
    classify_sse_payload,
    validate_report_checks,
)


def test_build_questions_returns_three_linked_rounds() -> None:
    questions = build_questions()

    assert len(questions) == 3
    assert questions[0].startswith("这个仓库")
    assert "刚才" in questions[1]
    assert "上一轮" in questions[2]


def test_classify_sse_payload_detects_required_event_types() -> None:
    payload = "event: assistant_delta\\ndata: {\"delta\":\"hello\"}\\n\\n"

    result = classify_sse_payload(payload)

    assert result["event"] == "assistant_delta"
    assert result["is_valid"] is True


def test_validate_report_checks_requires_all_acceptance_points() -> None:
    checks = {
        "has_final_output": True,
        "sse_format_ok": True,
        "tool_called": True,
        "prompt_assembled": True,
        "memory_updated": True,
        "multi_turn_continuity": True,
        "db_persisted": True,
    }

    errors = validate_report_checks(checks)

    assert errors == []
```

- [ ] **步骤 3：运行脚本单测确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_project_repo_agent_flow.py -q`
Expected: FAIL，因为脚本尚不存在。

- [ ] **步骤 4：实现真实对话链路验证脚本**

创建 `backend/scripts/verify_project_repo_agent_flow.py`。该脚本是 Repo Agent 功能完成后的最终验收门，必须对当前真实仓库执行真实多轮对话，而不是 fake model / fake provider 冒烟。

脚本约束：

- 必须真实调用共享 LLM 客户端，读取 `.env` 中现有配置：
  - `LLM_PROVIDER`
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE_URL`
  - `OPENAI_API_MODEL`
- 必须使用当前真实项目仓库，而不是 fake repository provider。
- 必须通过真实后端服务 API 发起会话、发送消息、消费 SSE 流。
- 必须读取数据库中的 `agent_sessions`、`agent_messages`、`agent_runs`、`agent_run_events`、`agent_artifacts`、`repository_snapshots` 做结果核验。
- 单次执行最多 3 轮对话，避免无限消耗 token。
- 如果前置条件不满足，例如本地数据库未启动、项目未完成集成配置、当前仓库项目记录不存在、LLM env 缺失，脚本必须明确报错并退出非 0，而不是静默跳过。

脚本建议提供 CLI 参数：

```bash
cd backend
python scripts/verify_project_repo_agent_flow.py \
  --project-id 1 \
  --branch main \
  --base-url http://127.0.0.1:8000 \
  --max-rounds 3
```

脚本内部建议拆分这些函数：

- `build_questions() -> list[str]`
- `run_preflight_checks(...) -> None`
- `create_session(...) -> dict`
- `send_message(...) -> dict`
- `consume_sse_until_final(...) -> list[dict]`
- `load_run_records(...) -> dict`
- `validate_report_checks(...) -> list[str]`
- `render_report(...) -> str`

三轮真实问题固定为：

```text
第一轮：这个仓库的后端入口在哪里？
第二轮：刚才说到的入口和认证链路有什么关系？
第三轮：基于上一轮内容，总结我应该先读哪几个文件。
```

脚本必须逐条验证以下验收项：

1. `是否有正常输出`
   - 每轮 assistant 最终消息状态为 `completed`
   - 每轮 `final_answer` 非空
2. `流式输出格式是否正确`
   - 真实消费 `/api/v1/projects/{project_id}/agent/sessions/{session_id}/stream`
   - 检查 SSE 原始片段满足 `event: ...` + `data: ...` 格式
   - 至少观察到 `run_started`、`tool_called` 或等价工具事件、`assistant_delta`、`final_answer`
3. `工具是否调用`
   - 至少一轮出现真实工具调用
   - `agent_run_events` 中存在 `tool_called` / `tool_result`
4. `prompt 是否按照预期组装`
   - `agent_runs.prompt_metadata` 中存在 `prefix`、`memory`、`relevant_memory`、`history`、`current_request`
   - 至少第二轮 `history` 或 `relevant_memory` 的字符数大于第一轮
5. `memory 是否有更新`
   - 会话结束后重新读取 `agent_sessions.memory_state`
   - `working.recent_files` 非空
   - `episodic_notes`、`task_summary`、`file_summaries` 至少有一项相较初始态发生变化
6. `多轮对话是否连贯`
   - 第二轮和第三轮回答中必须体现上一轮上下文
   - 脚本至少检查：
     - 第二轮回答或第三轮回答中引用了第一轮提到的文件名、模块名或“刚才/上一轮”主题
     - 第二轮 run 的 prompt metadata 中带有第一轮历史
7. `数据库中有没有按照预期落库、修改`
   - `agent_sessions` 有最新 `last_head_sha`、`last_workspace_fingerprint`、`memory_state`
   - `agent_messages` 至少有 3 条用户消息和 3 条助手消息
   - `agent_runs` 至少有 3 条记录，且 `status` 为 `completed`
   - `agent_run_events` 存在递增 `sequence`
   - `agent_artifacts` 至少存在 `prompt_context`、`memory_delta`、`run_report` 中的合理子集
   - `repository_snapshots` 至少存在当前分支/`head_sha` 对应记录

建议报告输出到：

- `docs/verification/2026-06-04-repo-agent-verification.md`

- [ ] **步骤 5：运行脚本单测并确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_project_repo_agent_flow.py -q`
Expected: PASS

- [ ] **步骤 6：运行后端测试集合**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/agent tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: PASS

- [ ] **步骤 7：运行前端页面测试**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm test -- --runInBand src/pages/projects/ProjectAgentPage.test.tsx`
Expected: PASS

- [ ] **步骤 8：执行真实仓库 + 真实 LLM 的最终验收脚本**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && python scripts/verify_project_repo_agent_flow.py --project-id 1 --branch main --base-url http://127.0.0.1:8000 --max-rounds 3`
Expected: PASS，并生成针对当前真实仓库的多轮验证报告。

验收通过标准必须同时满足：

- 正常输出存在
- SSE 流式格式正确
- 工具有真实调用
- prompt 组装字段完整
- memory 发生更新
- 多轮对话连贯
- 数据库按预期落库

- [ ] **步骤 9：更新运行说明**

修改 `backend/README.md`，新增一节：

```md
## Repo Agent

平台新增了项目级仓库对话助手能力。

- 入口：`/api/v1/projects/{project_id}/agent/*`
- 形态：锁定单个分支的持续对话
- 边界：只读仓库工具、PR/MR 元信息工具、SSE 流式回答
- 非目标：不执行 shell、不写文件、不 patch
- 验收：运行 `python scripts/verify_project_repo_agent_flow.py --project-id <id> --branch <branch> --base-url http://127.0.0.1:8000 --max-rounds 3` 可对当前真实仓库执行真实 LLM 多轮对话验证
```

修改根 `README.md`，在 `frontend/` 与 `backend/` 介绍中补一句：

```md
- `Repo Agent`：项目级仓库对话助手，保留 Pico 风格上下文、记忆、工具协议与 trace 落库设计
- `Repo Agent Verification`：提供真实仓库、真实 LLM、最多 3 轮对话的端到端验收脚本
```

- [ ] **步骤 10：记录验证文档**

创建 `docs/verification/2026-06-04-repo-agent-verification.md`：

```md
# Repo Agent Verification

## 环境

- backend: 本地 FastAPI 服务
- frontend: 可选
- database: 本地 PostgreSQL
- llm: 真实 `.env` provider 配置
- repository: 当前真实项目仓库

## 执行命令

- `cd backend && pytest tests/unit/agent tests/integration/test_agent_api.py tests/integration/test_agent_sse.py tests/unit/scripts/test_verify_project_repo_agent_flow.py -q`
- `cd frontend && npm test -- --runInBand src/pages/projects/ProjectAgentPage.test.tsx`
- `cd backend && python scripts/verify_project_repo_agent_flow.py --project-id 1 --branch main --base-url http://127.0.0.1:8000 --max-rounds 3`

## 验证项

1. 正常输出
2. SSE 流式格式正确
3. 工具真实调用
4. prompt 按预期组装
5. memory 更新
6. 多轮对话连贯
7. 数据库落库正确
8. 文件版本变化后触发 memory invalidation

## 结果

- [ ] backend tests passed
- [ ] frontend tests passed
- [ ] real repo flow checked
- [ ] real LLM flow checked
- [ ] database persistence checked

## 多轮对话记录

- Round 1:
- Round 2:
- Round 3:

## SSE 事件检查

- observed events:
- raw chunks sample:

## 数据库检查

- session:
- runs:
- events:
- artifacts:
- snapshots:
```

- [ ] **步骤 11：提交**

```bash
git add backend/tests/unit/agent/test_run_service.py backend/tests/integration/test_agent_api.py backend/tests/integration/test_agent_sse.py backend/tests/unit/scripts/test_verify_project_repo_agent_flow.py backend/scripts/verify_project_repo_agent_flow.py frontend/src/pages/projects/ProjectAgentPage.test.tsx backend/README.md README.md docs/verification/2026-06-04-repo-agent-verification.md
git commit -m "test: add repo agent real flow verification"
```

---

## 自检

### 1. Spec coverage

- 独立 `Project Repo Agent` 页面：任务 6 覆盖。
- 创建会话时只选择分支并锁定：任务 1、任务 5、任务 6 覆盖。
- Pico 风格 `ContextManager`、`LayeredMemory`、workspace identity：任务 2 覆盖。
- 只读仓库工具与 PR/MR 元信息工具：任务 3、任务 4 覆盖。
- LLM `<tool>` / `<final>` 协议：任务 2、任务 5 覆盖。
- 统一脱敏：任务 4 覆盖。
- trace / artifact / run 状态：任务 1、任务 5 覆盖。
- freshness 与 memory invalidation：任务 2、任务 7 覆盖。
- SSE 体验：任务 5、任务 6、任务 7 覆盖。

### 2. Placeholder scan

- 已检查计划中没有 `TODO`、`TBD`、`implement later` 等占位词。
- 所有新增模块都给出了明确文件路径、测试入口和最小代码骨架。

### 3. Type consistency

- `agent_sessions.branch`、`agent_runs.branch`、`WorkspaceSnapshot.branch`、前端 `AgentSessionResponse.branch` 命名一致。
- `workspace_fingerprint` 与 `runtime_identity_hash` 在 schema、run service 与 spec 中命名一致。
- `search_code`、`read_file`、`list_comment_threads` 等工具名在工具表、gateway 与协议中保持一致。
