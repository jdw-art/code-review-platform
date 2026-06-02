# Pico Online 仓库理解助手实施计划

> **给 agentic workers：** 必须使用子技能 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项实施本计划。步骤使用 checkbox（`- [ ]`）语法跟踪进度。

**目标：** 在现有 FastAPI 代码审查平台内，实现一个只读的项目级仓库理解助手，并保留 Pico 的上下文、记忆、工具网关、run、event 与 artifact 模型。

**架构：** 新增 `backend/app/agent/` 领域模块，复用 Pico 风格的上下文和记忆概念，同时把本地文件系统与本地 session store 替换为 PostgreSQL、GitHub/GitLab 仓库 provider、FastAPI API 与 SSE 事件。第一版严格只读：不开放 shell、不写文件、不 patch、不 delegate、不做 checkpoint、不做 resume。

**技术栈：** FastAPI、SQLAlchemy、Alembic、PostgreSQL JSON columns、pytest、React + Vite + TypeScript、React Query、浏览器 EventSource/SSE。

---

## 文件结构

新增这些后端领域文件：

- `backend/app/db/models/agent_session.py`：存储项目级 agent session 与 Pico memory state。
- `backend/app/db/models/agent_message.py`：存储用户可见的聊天消息。
- `backend/app/db/models/agent_run.py`：存储一次 Pico 风格的 `ask()` 执行。
- `backend/app/db/models/agent_run_event.py`：存储 trace/SSE 事件。
- `backend/app/db/models/agent_artifact.py`：存储 run artifacts 与工具缓存条目。
- `backend/app/db/models/repository_snapshot.py`：存储轻量 workspace snapshot。
- `backend/app/schemas/agent.py`：定义 session、message、run 与 SSE 事件相关的 Pydantic 请求/响应模型。
- `backend/app/agent/memory.py`：从 `pico/pico/memory.py` 复制/改造 Pico memory state 默认值与更新 helper。
- `backend/app/agent/context.py`：从 `pico/pico/context_manager.py` 复制/改造 Pico 风格上下文组装逻辑。
- `backend/app/agent/workspace.py`：平台版 `WorkspaceContext` 与 fingerprint builder。
- `backend/app/agent/tools.py`：只读工具规格与参数校验。
- `backend/app/agent/tool_gateway.py`：工具存在性检查、参数校验、重复调用拦截、权限 hook、缓存、执行、脱敏、裁剪、记录。
- `backend/app/agent/repository_provider.py`：provider protocol 与测试用 fake provider。
- `backend/app/agent/snapshot_service.py`：轻量 snapshot 创建与 stale 检测。
- `backend/app/agent/run_service.py`：Pico 风格多步 agent run loop。
- `backend/app/agent/event_recorder.py`：事件持久化与 stream polling helper。
- `backend/app/services/agent_session_service.py`：session/message/run 持久化编排。
- `backend/app/api/routes/agent.py`：agent sessions、messages、runs、snapshot refresh 与 stream 的 FastAPI routes。

修改这些后端文件：

- `backend/app/db/models/__init__.py`：导出新的 ORM models。
- `backend/app/db/base.py`：如果 model import 已通过 `models/__init__.py` 串好，预期不需要改；实施时验证 metadata discovery。
- `backend/app/api/router.py`：include agent router。
- `backend/alembic/versions/0004_create_pico_online_agent_schema.py`：创建 agent 与 snapshot 表。

新增或修改这些后端测试：

- `backend/tests/unit/db/test_agent_models_schema.py`
- `backend/tests/unit/agent/test_memory_context.py`
- `backend/tests/unit/agent/test_tool_gateway.py`
- `backend/tests/unit/agent/test_snapshot_service.py`
- `backend/tests/unit/agent/test_run_service.py`
- `backend/tests/integration/test_agent_api.py`
- `backend/tests/integration/test_agent_sse.py`

新增这些前端文件：

- `frontend/src/features/agent/api.ts`：Agent API 与 EventSource helper。
- `frontend/src/pages/projects/ProjectAgentPage.tsx`：仓库助手页面。
- `frontend/src/pages/projects/ProjectAgentPage.test.tsx`：前端行为测试。

修改这些前端文件：

- `frontend/src/routes/router.tsx`：新增 project agent route。
- `frontend/src/pages/projects/ProjectListPage.tsx`：新增进入 agent 页的操作按钮或链接。
- `frontend/src/lib/api/types.ts`：如果共享类型集中维护，在这里新增 agent response types。

---

### 任务 1：新增 Agent 数据库 schema

**文件：**
- 新增：`backend/app/db/models/agent_session.py`
- 新增：`backend/app/db/models/agent_message.py`
- 新增：`backend/app/db/models/agent_run.py`
- 新增：`backend/app/db/models/agent_run_event.py`
- 新增：`backend/app/db/models/agent_artifact.py`
- 新增：`backend/app/db/models/repository_snapshot.py`
- 新增：`backend/alembic/versions/0004_create_pico_online_agent_schema.py`
- 修改：`backend/app/db/models/__init__.py`
- 测试：`backend/tests/unit/db/test_agent_models_schema.py`

- [ ] **步骤 1：先写失败的 schema 测试**

创建 `backend/tests/unit/db/test_agent_models_schema.py`：

```python
from __future__ import annotations

from sqlalchemy import inspect

from app.db.base import Base


def test_agent_tables_are_registered() -> None:
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
        "provider",
        "model",
        "workspace_fingerprint",
        "snapshot_id",
        "memory_state",
        "settings",
        "last_message_at",
        "created_at",
        "updated_at",
    } <= columns
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`cd backend && pytest tests/unit/db/test_agent_models_schema.py -q`

预期：失败，因为 agent tables 还不存在。

- [ ] **步骤 3：新增 ORM models**

创建 `backend/app/db/models/repository_snapshot.py`：

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class RepositorySnapshot(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repository_snapshots"
    __table_args__ = (
        Index("ix_repository_snapshots_project_ref_head", "project_id", "ref", "head_sha"),
        Index("ix_repository_snapshots_fingerprint", "fingerprint", unique=True),
    )

    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(32), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default=text("'pending'"))
    file_tree: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    overview: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    recent_commits: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    indexed_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project")
```

创建其他 model 文件，沿用同样的 `BigIntPrimaryKeyMixin` 与 `TimestampMixin` 风格：

```python
# backend/app/db/models/agent_session.py
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AgentSession(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (Index("ix_agent_sessions_project_updated", "project_id", "updated_at"),)

    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default=text("'active'"))
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workspace_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default=text("''"))
    snapshot_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("repository_snapshots.id", ondelete="SET NULL"), nullable=True)
    memory_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    last_message_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project")
    snapshot = relationship("RepositorySnapshot")
```

按照已批准 spec 中的字段，为 `AgentMessage`、`AgentRun`、`AgentRunEvent`、`AgentArtifact` 创建等价定义。

- [ ] **步骤 4：导出 models**

修改 `backend/app/db/models/__init__.py`，新增 import：

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

创建 `backend/alembic/versions/0004_create_pico_online_agent_schema.py`，使用 `revision = "0004_pico_online_agent_schema"` 与 `down_revision = "0003_webhook_review_execution"`。创建六张表、JSON 默认值、外键和索引，字段与 ORM models 保持一致。

- [ ] **步骤 6：运行 schema 测试**

运行：`cd backend && pytest tests/unit/db/test_agent_models_schema.py -q`

预期：通过。

- [ ] **步骤 7：提交**

```bash
git add backend/app/db/models backend/alembic/versions/0004_create_pico_online_agent_schema.py backend/tests/unit/db/test_agent_models_schema.py
git commit -m "feat: add pico online agent schema"
```

---

### 任务 2：新增 Pico 风格 memory 与 context core

**文件：**
- 新增：`backend/app/agent/__init__.py`
- 新增：`backend/app/agent/memory.py`
- 新增：`backend/app/agent/context.py`
- 新增：`backend/app/agent/workspace.py`
- 测试：`backend/tests/unit/agent/test_memory_context.py`

- [ ] **步骤 1：先写失败的 memory/context 测试**

创建 `backend/tests/unit/agent/test_memory_context.py`：

```python
from __future__ import annotations

from app.agent.context import ContextManager
from app.agent.memory import default_memory_state
from app.agent.workspace import WorkspaceContext


def test_default_memory_state_matches_pico_shape() -> None:
    state = default_memory_state()

    assert state["working"] == {"task_summary": "", "recent_files": []}
    assert state["episodic_notes"] == []
    assert state["file_summaries"] == {}
    assert state["task"] == ""
    assert state["files"] == []
    assert state["notes"] == []
    assert state["next_note_index"] == 0


def test_context_manager_keeps_current_request_and_workspace() -> None:
    workspace = WorkspaceContext(
        project_id=1,
        project_name="Demo",
        platform_type="github",
        repo_url="https://example.com/demo.git",
        ref="main",
        head_sha="abc123",
        fingerprint="fp-demo",
        overview={"readme": "Demo README"},
        recent_commits=[],
    )
    manager = ContextManager(
        workspace_text=workspace.text(),
        memory_state=default_memory_state(),
        history=[{"role": "user", "content": "上一轮问认证"}],
    )

    prompt, metadata = manager.build("那权限在哪里校验？")

    assert "Workspace:" in prompt
    assert "Demo README" in prompt
    assert "上一轮问认证" in prompt
    assert "那权限在哪里校验？" in prompt
    assert metadata["prompt_chars"] == len(prompt)
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`cd backend && pytest tests/unit/agent/test_memory_context.py -q`

预期：失败，因为 `app.agent` 还不存在。

- [ ] **步骤 3：新增 memory helper**

创建 `backend/app/agent/memory.py`：

```python
from __future__ import annotations


def default_memory_state() -> dict[str, object]:
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
```

- [ ] **步骤 4：新增 workspace context**

创建 `backend/app/agent/workspace.py`，实现一个 dataclass，负责渲染平台版 workspace prefix，并根据 project/snapshot payload 计算确定性的 fingerprint。

- [ ] **步骤 5：新增 context manager**

创建 `backend/app/agent/context.py`，实现精简版 Pico-style context manager：渲染 `Prefix`、`Memory`、`History`、`Current user request`，应用 section budgets，并返回包含各 section 长度的 prompt metadata。

- [ ] **步骤 6：运行测试**

运行：`cd backend && pytest tests/unit/agent/test_memory_context.py -q`

预期：通过。

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent backend/tests/unit/agent/test_memory_context.py
git commit -m "feat: add pico agent context core"
```

---

### 任务 3：实现只读工具网关

**文件：**
- 新增：`backend/app/agent/tools.py`
- 新增：`backend/app/agent/tool_gateway.py`
- 新增：`backend/app/agent/repository_provider.py`
- 测试：`backend/tests/unit/agent/test_tool_gateway.py`

- [ ] **步骤 1：先写失败的工具网关测试**

创建 `backend/tests/unit/agent/test_tool_gateway.py`，覆盖：

```text
test_gateway_rejects_unknown_tool: call gateway.execute("missing_tool", {}) and assert ValueError contains "unknown tool".
test_gateway_validates_read_file_line_range: call read_file with start=10,end=1 and assert ValueError contains "invalid line range".
test_gateway_blocks_third_identical_recent_tool_call: seed two identical tool history entries and assert the third matching call returns a blocked result.
test_gateway_reuses_same_run_cache_for_same_snapshot: call read_file twice with the same args and assert provider.read_file is called once.
test_gateway_redacts_secret_like_output_before_returning: fake provider returns "token=sk-secret123456" and gateway output contains "<redacted>".
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`cd backend && pytest tests/unit/agent/test_tool_gateway.py -q`

预期：失败，因为工具网关还不存在。

- [ ] **步骤 3：定义 provider protocol**

创建 `backend/app/agent/repository_provider.py`：

```python
from __future__ import annotations

from typing import Protocol


class RepositoryContentProvider(Protocol):
    def list_files(self, *, path: str, ref: str) -> str:
        pass

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        pass

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        pass

    def get_project_overview(self) -> str:
        pass

    def get_recent_commits(self, *, limit: int) -> str:
        pass
```

- [ ] **步骤 4：定义只读工具与参数校验**

创建 `backend/app/agent/tools.py`，为 `list_files`、`read_file`、`search`、`get_project_overview`、`get_recent_commits` 定义 specs。实现以下校验：空 path、非法行号范围、空 search pattern、`limit` 不在 `1..50`。

- [ ] **步骤 5：实现网关执行链路**

创建 `backend/app/agent/tool_gateway.py`，实现：

```text
exists -> validate -> repeated guard -> cache lookup -> execute -> redact -> clip -> cache store -> return
```

重复调用拦截必须匹配 Pico 当前行为：如果最近两个 tool history events 的 `name` 和 `args` 都与当前调用一致，则拒绝本次调用。

- [ ] **步骤 6：运行测试**

运行：`cd backend && pytest tests/unit/agent/test_tool_gateway.py -q`

预期：通过。

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent/tools.py backend/app/agent/tool_gateway.py backend/app/agent/repository_provider.py backend/tests/unit/agent/test_tool_gateway.py
git commit -m "feat: add read-only agent tool gateway"
```

---

### 任务 4：新增 Repository Snapshot Service

**文件：**
- 新增：`backend/app/agent/snapshot_service.py`
- 测试：`backend/tests/unit/agent/test_snapshot_service.py`

- [ ] **步骤 1：先写失败的 snapshot tests**

创建 `backend/tests/unit/agent/test_snapshot_service.py`，覆盖：

```text
test_snapshot_service_creates_ready_snapshot_for_project: create a Project and fake provider head_sha="sha1"; assert a ready RepositorySnapshot is committed.
test_snapshot_service_marks_existing_snapshot_stale_when_head_changes: seed a ready snapshot with head_sha="old"; call mark_stale_snapshots with "new"; assert old snapshot status is "stale".
test_snapshot_fingerprint_changes_when_head_sha_changes: call build_fingerprint twice with different head_sha values and assert the hashes differ.
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`cd backend && pytest tests/unit/agent/test_snapshot_service.py -q`

预期：失败，因为 `RepositorySnapshotService` 还不存在。

- [ ] **步骤 3：实现 snapshot service**

创建 `backend/app/agent/snapshot_service.py`，包含方法：

```python
class RepositorySnapshotService:
    def ensure_ready_snapshot(self, *, project, provider) -> RepositorySnapshot:
        """Create or return a ready snapshot for the project's default branch."""

    def mark_stale_snapshots(self, *, project_id: int, ref: str, new_head_sha: str) -> None:
        """Mark ready snapshots stale when their head sha differs from new_head_sha."""

    def build_fingerprint(self, *, project_id: int, platform_type: str, repo_url: str | None, ref: str, head_sha: str, tool_signature: str, settings_hash: str) -> str:
        """Return a sha256 hash for the snapshot identity payload."""
```

使用 provider 方法获取 `head_sha`、`file_tree`、`overview` 与 `recent_commits`。

- [ ] **步骤 4：运行测试**

运行：`cd backend && pytest tests/unit/agent/test_snapshot_service.py -q`

预期：通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/agent/snapshot_service.py backend/tests/unit/agent/test_snapshot_service.py
git commit -m "feat: add repository snapshot service"
```

---

### 任务 5：使用 Fake Model 实现 Agent Run Service

**文件：**
- 新增：`backend/app/agent/run_service.py`
- 新增：`backend/app/agent/event_recorder.py`
- 新增：`backend/app/services/agent_session_service.py`
- 测试：`backend/tests/unit/agent/test_run_service.py`

- [ ] **步骤 1：先写失败的 run service tests**

创建 `backend/tests/unit/agent/test_run_service.py`，覆盖：

```text
test_run_service_completes_final_answer: fake model returns "Final answer"; assert run.status == "completed" and assistant message contains it.
test_run_service_executes_tool_then_completes: fake model returns a read_file tool envelope then final text; assert one tool_result event exists.
test_run_service_stops_at_step_limit: fake model repeatedly returns a search tool call; set max_steps=1 and assert stop_reason == "step_limit_reached".
test_run_service_persists_updated_memory_state: run completes after reading README.md; assert session.memory_state["working"]["recent_files"] includes README.md.
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`cd backend && pytest tests/unit/agent/test_run_service.py -q`

预期：失败，因为 `AgentRunService` 还不存在。

- [ ] **步骤 3：实现 event recorder**

创建 `backend/app/agent/event_recorder.py`：

```python
class AgentEventRecorder:
    def record(self, *, run_id: int, session_id: int, event_type: str, payload: dict) -> None:
        """Persist an AgentRunEvent with the next sequence for this run."""

    def list_after(self, *, session_id: int, after_id: int | None = None) -> list[AgentRunEvent]:
        """Return session events with id greater than after_id ordered by id."""
```

- [ ] **步骤 4：实现 session persistence service**

创建 `backend/app/services/agent_session_service.py`，实现创建 sessions、messages、runs，以及 run 完成后更新 assistant message 的方法。

- [ ] **步骤 5：实现 run service**

创建 `backend/app/agent/run_service.py`，实现有界循环：

```text
load run -> build context -> call fake/model client -> parse final or tool -> execute gateway -> record events -> update message/run/memory
```

第一版使用简单 JSON tool-call envelope：

```json
{"tool": {"name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20}}}
```

任何非 tool 文本响应都视作 final answer。

- [ ] **步骤 6：运行测试**

运行：`cd backend && pytest tests/unit/agent/test_run_service.py -q`

预期：通过。

- [ ] **步骤 7：提交**

```bash
git add backend/app/agent/run_service.py backend/app/agent/event_recorder.py backend/app/services/agent_session_service.py backend/tests/unit/agent/test_run_service.py
git commit -m "feat: add pico-style agent run service"
```

---

### 任务 6：新增 Agent API 与 SSE

**文件：**
- 新增：`backend/app/schemas/agent.py`
- 新增：`backend/app/api/routes/agent.py`
- 修改：`backend/app/api/router.py`
- 测试：`backend/tests/integration/test_agent_api.py`
- 测试：`backend/tests/integration/test_agent_sse.py`

- [ ] **步骤 1：先写失败的 API tests**

创建 `backend/tests/integration/test_agent_api.py`，覆盖：

```text
test_agent_session_message_and_run_flow: create a project, POST a session, POST a message, assert user_message_id, assistant_message_id, and run_id are integers.
test_agent_endpoints_require_project_read_permission: unauthenticated or limited client receives 403 for session list and message create routes.
test_agent_snapshot_refresh_requires_project_update_permission: user with only project:read receives 403 for snapshot refresh.
```

- [ ] **步骤 2：先写失败的 SSE test**

创建 `backend/tests/integration/test_agent_sse.py`，覆盖：`GET /api/v1/agent/sessions/{session_id}/stream?since_event_id=0` 能返回 SSE 格式的已有 events。

- [ ] **步骤 3：运行测试，确认失败**

运行：`cd backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

预期：失败，因为 routes 还不存在。

- [ ] **步骤 4：新增 schemas**

创建 `backend/app/schemas/agent.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentSessionCreateRequest(BaseModel):
    title: str = "仓库助手"


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    status: str
    workspace_fingerprint: str
    snapshot_id: int | None
    created_at: datetime
    updated_at: datetime


class AgentMessageCreateRequest(BaseModel):
    content: str


class AgentMessageAcceptedResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    run_id: int
    status: str


class AgentMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    run_id: int | None
    role: str
    content: str
    content_format: str
    status: str
    sequence: int
    metadata: dict[str, Any]
    created_at: datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    project_id: int
    status: str
    stop_reason: str
    tool_steps: int
    attempts: int
    last_tool: str
    final_answer: str | None
```

- [ ] **步骤 5：新增 routes**

创建 `backend/app/api/routes/agent.py`，实现已批准 routes：

```text
GET    /projects/{project_id}/agent/sessions
POST   /projects/{project_id}/agent/sessions
GET    /agent/sessions/{session_id}
GET    /agent/sessions/{session_id}/messages
POST   /agent/sessions/{session_id}/messages
GET    /agent/sessions/{session_id}/stream
POST   /agent/sessions/{session_id}/snapshot/refresh
GET    /agent/runs/{run_id}
```

读路由和 message creation 使用 `require_permission("project:read")`；snapshot refresh 使用 `require_permission("project:update")`。

- [ ] **步骤 6：include router**

修改 `backend/app/api/router.py`：

```python
from app.api.routes.agent import router as agent_router

api_router.include_router(agent_router)
```

- [ ] **步骤 7：运行 API/SSE tests**

运行：`cd backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

预期：通过。

- [ ] **步骤 8：提交**

```bash
git add backend/app/schemas/agent.py backend/app/api/routes/agent.py backend/app/api/router.py backend/tests/integration/test_agent_api.py backend/tests/integration/test_agent_sse.py
git commit -m "feat: add agent api and event stream"
```

---

### 任务 7：新增前端仓库助手页面

**文件：**
- 新增：`frontend/src/features/agent/api.ts`
- 新增：`frontend/src/pages/projects/ProjectAgentPage.tsx`
- 新增：`frontend/src/pages/projects/ProjectAgentPage.test.tsx`
- 修改：`frontend/src/routes/router.tsx`
- 修改：`frontend/src/pages/projects/ProjectListPage.tsx`
- 修改：`frontend/src/lib/api/types.ts`

- [ ] **步骤 1：先写失败的前端测试**

创建 `frontend/src/pages/projects/ProjectAgentPage.test.tsx`，覆盖：

```tsx
it("renders sessions, sends a message, and appends streamed assistant text", async () => {
  // mock list/create session, post message, and EventSource events
});
```

- [ ] **步骤 2：运行前端测试，确认失败**

运行：`cd frontend && npm test -- ProjectAgentPage.test.tsx --runInBand`

预期：失败，因为页面和 API module 还不存在。

- [ ] **步骤 3：新增 API client**

创建 `frontend/src/features/agent/api.ts`：

```ts
import { apiRequest } from "../../lib/api/http";

export async function listAgentSessions(projectId: number) {
  return apiRequest(`/projects/${projectId}/agent/sessions`);
}

export async function createAgentSession(projectId: number, title: string) {
  return apiRequest(`/projects/${projectId}/agent/sessions`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function listAgentMessages(sessionId: number) {
  return apiRequest(`/agent/sessions/${sessionId}/messages`);
}

export async function sendAgentMessage(sessionId: number, content: string) {
  return apiRequest(`/agent/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function createAgentEventSource(sessionId: number, runId?: number) {
  const params = runId ? `?run_id=${runId}` : "";
  return new EventSource(`/api/v1/agent/sessions/${sessionId}/stream${params}`);
}
```

- [ ] **步骤 4：新增页面组件**

创建 `frontend/src/pages/projects/ProjectAgentPage.tsx`，包含：

- session 列表。
- 消息流。
- 输入表单。
- snapshot 状态面板。
- tool event 面板。
- EventSource 生命周期 cleanup。

- [ ] **步骤 5：接入 route 与项目入口**

在 `frontend/src/routes/router.tsx` 添加 `/projects/:projectId/agent` route。在 `ProjectListPage` 的行操作里添加进入该 route 的按钮或链接。

- [ ] **步骤 6：运行前端测试**

运行：`cd frontend && npm test -- ProjectAgentPage.test.tsx --runInBand`

预期：通过。

- [ ] **步骤 7：提交**

```bash
git add frontend/src/features/agent/api.ts frontend/src/pages/projects/ProjectAgentPage.tsx frontend/src/pages/projects/ProjectAgentPage.test.tsx frontend/src/routes/router.tsx frontend/src/pages/projects/ProjectListPage.tsx frontend/src/lib/api/types.ts
git commit -m "feat: add project repository assistant page"
```

---

### 任务 8：运行完整验证并更新文档

**文件：**
- 修改：`backend/README.md`
- 修改：`README.md`
- 新增：`backend/scripts/verify_pico_online_agent_flow.py`
- 新增：`docs/verification/2026-06-03-pico-online-agent-mvp.md`

- [ ] **步骤 1：运行后端 unit 与 integration tests**

运行：`cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

预期：通过。

- [ ] **步骤 2：运行前端 tests**

运行：`cd frontend && npm test -- --run`

预期：通过。

- [ ] **步骤 3：更新文档**

更新 `README.md` 与 `backend/README.md`，补充新的项目级仓库助手能力、route 摘要与只读范围。

- [ ] **步骤 4：新增真实对话链路验证脚本**

创建 `backend/scripts/verify_pico_online_agent_flow.py`。脚本需要在本地 backend 环境中执行一条最多 3 轮的仓库助手对话链路，并输出 Markdown 验证报告。脚本可以使用 fake model 与 fake repository provider，但必须走真实的 `AgentSessionService`、`AgentRunService`、`AgentToolGateway`、`AgentEventRecorder` 与数据库持久化。

脚本至少验证这些断言：

```text
1. 正常输出：每轮 assistant message 最终状态为 completed，final_answer 非空。
2. 流式格式：agent_run_events 中包含 run_started、assistant_delta 或 assistant_message、final，事件 sequence 单调递增。
3. 工具调用：至少一轮包含 tool_start 与 tool_result，工具名为 read_file 或 search。
4. prompt 组装：agent_runs.prompt_metadata 包含 prefix、memory、history、current_request 的 rendered chars 或等价 section metadata。
5. memory 更新：第三轮结束后 agent_sessions.memory_state["working"]["recent_files"] 非空，且 task_summary 或 notes 体现本轮对话主题。
6. 多轮连贯：第二轮和第三轮的问题使用“它/刚才/上一轮”这类指代，fake model 需要能从 prompt history 或 memory 中看到上一轮内容，并在回答中引用上一轮主题。
```

建议三轮测试问题：

```text
第一轮：这个仓库的后端入口在哪里？
第二轮：刚才说到的入口和认证链路有什么关系？
第三轮：基于上一轮内容，总结我应该先读哪几个文件。
```

运行：

```bash
cd backend
python scripts/verify_pico_online_agent_flow.py
```

预期：脚本退出码为 0，并生成 `docs/verification/2026-06-03-pico-online-agent-mvp.md`。

- [ ] **步骤 5：运行真实对话链路验证脚本**

运行：`cd backend && python scripts/verify_pico_online_agent_flow.py`

预期：通过，并生成包含 3 轮对话结果、SSE/event 格式检查、工具调用检查、prompt metadata 检查、memory 更新检查、多轮连贯性检查的 Markdown 报告。

- [ ] **步骤 6：写验证记录**

创建 `docs/verification/2026-06-03-pico-online-agent-mvp.md`：

```markdown
# Pico Online Agent MVP Verification

## Commands

- `cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
- `cd frontend && npm test -- --run`
- `cd backend && python scripts/verify_pico_online_agent_flow.py`

## Result

Backend tests, frontend tests, and the real conversation flow verification script passed.

## Scope Confirmed

- Read-only tools only.
- No shell/write/patch/delegate.
- Session, messages, runs, events, artifacts, and snapshots persist in PostgreSQL.
- SSE stream can replay events.

## Real Conversation Flow

- Round count: 3
- Final answers: all non-empty
- Stream events: run_started/tool_start/tool_result/assistant_delta/final observed in order
- Tool calls: at least one read_file or search call observed
- Prompt metadata: prefix, memory, history, and current_request sections recorded
- Memory update: recent_files and task summary/notes updated after the run
- Multi-turn continuity: round 2 and round 3 answers reference prior-round context
```

- [ ] **步骤 7：提交**

```bash
git add README.md backend/README.md backend/scripts/verify_pico_online_agent_flow.py docs/verification/2026-06-03-pico-online-agent-mvp.md
git commit -m "docs: verify pico online agent mvp"
```

---

## 自检

Spec 覆盖情况：

- 数据模型要求由任务 1 覆盖。
- Pico context 与 memory 保留由任务 2 覆盖。
- 工具存在性、参数校验、重复调用拦截、缓存、脱敏、裁剪、记录由任务 3 覆盖。
- 轻量 snapshot 与 fingerprint 策略由任务 4 覆盖。
- 多步 run loop 与 memory 持久化由任务 5 覆盖。
- API 与 SSE 协议由任务 6 覆盖。
- 项目级前端入口由任务 7 覆盖。
- 验证、真实对话链路检查与文档由任务 8 覆盖。

实施边界：

- 本计划明确不包含 shell/write/patch/delegate/checkpoint/resume。
- 本计划明确不包含完整 RAG 与 embedding。
- 本计划先用 fake model/provider 测试核心链路，再接入真实 provider，以保证早期任务可确定、可验证。
