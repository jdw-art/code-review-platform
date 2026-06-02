# Pico Online Repo Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only project-level repository understanding assistant that preserves Pico's context, memory, tool gateway, run, event, and artifact model inside the existing FastAPI code review platform.

**Architecture:** Add an `backend/app/agent/` domain that reuses Pico-style context and memory concepts while replacing local filesystem/session stores with PostgreSQL, GitHub/GitLab repository providers, FastAPI APIs, and SSE events. The first release is read-only: no shell, no write, no patch, no delegate, no checkpoint, and no resume.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL JSON columns, pytest, React + Vite + TypeScript, React Query, browser EventSource/SSE.

---

## File Structure

Create these backend domain files:

- `backend/app/db/models/agent_session.py`: Stores project-level agent sessions and Pico memory state.
- `backend/app/db/models/agent_message.py`: Stores user-visible chat messages.
- `backend/app/db/models/agent_run.py`: Stores one Pico-style `ask()` execution.
- `backend/app/db/models/agent_run_event.py`: Stores trace/SSE events.
- `backend/app/db/models/agent_artifact.py`: Stores run artifacts and tool cache entries.
- `backend/app/db/models/repository_snapshot.py`: Stores lightweight workspace snapshots.
- `backend/app/schemas/agent.py`: Pydantic request/response models for sessions, messages, runs, and SSE-facing event payloads.
- `backend/app/agent/memory.py`: Pico memory state defaults and update helpers copied/adapted from `pico/pico/memory.py`.
- `backend/app/agent/context.py`: Pico-style context assembly copied/adapted from `pico/pico/context_manager.py`.
- `backend/app/agent/workspace.py`: Platform `WorkspaceContext` and fingerprint builder.
- `backend/app/agent/tools.py`: Read-only tool specs and validation.
- `backend/app/agent/tool_gateway.py`: Tool existence check, validation, repeated-call guard, authorization hook, cache, execute, sanitize, clip, record.
- `backend/app/agent/repository_provider.py`: Provider protocol plus fake provider for tests.
- `backend/app/agent/snapshot_service.py`: Lightweight snapshot creation and stale detection.
- `backend/app/agent/run_service.py`: Pico-style multi-step agent run loop.
- `backend/app/agent/event_recorder.py`: Event persistence and stream polling helpers.
- `backend/app/services/agent_session_service.py`: Session/message/run persistence orchestration.
- `backend/app/api/routes/agent.py`: FastAPI routes for agent sessions, messages, runs, snapshot refresh, and stream.

Modify these existing backend files:

- `backend/app/db/models/__init__.py`: Export new ORM models.
- `backend/app/db/base.py`: No change expected if model imports are wired through `models/__init__.py`; verify metadata discovery.
- `backend/app/api/router.py`: Include agent router.
- `backend/alembic/versions/0004_create_pico_online_agent_schema.py`: Create agent and snapshot tables.

Create or modify these backend tests:

- `backend/tests/unit/db/test_agent_models_schema.py`
- `backend/tests/unit/agent/test_memory_context.py`
- `backend/tests/unit/agent/test_tool_gateway.py`
- `backend/tests/unit/agent/test_snapshot_service.py`
- `backend/tests/unit/agent/test_run_service.py`
- `backend/tests/integration/test_agent_api.py`
- `backend/tests/integration/test_agent_sse.py`

Create these frontend files:

- `frontend/src/features/agent/api.ts`: Agent API and EventSource helpers.
- `frontend/src/pages/projects/ProjectAgentPage.tsx`: Repository assistant page.
- `frontend/src/pages/projects/ProjectAgentPage.test.tsx`: Frontend behavior tests.

Modify these frontend files:

- `frontend/src/routes/router.tsx`: Add project agent route.
- `frontend/src/pages/projects/ProjectListPage.tsx`: Add entry action or link to the agent page.
- `frontend/src/lib/api/types.ts`: Add agent response types if shared types are kept centralized.

---

### Task 1: Add Agent Database Schema

**Files:**
- Create: `backend/app/db/models/agent_session.py`
- Create: `backend/app/db/models/agent_message.py`
- Create: `backend/app/db/models/agent_run.py`
- Create: `backend/app/db/models/agent_run_event.py`
- Create: `backend/app/db/models/agent_artifact.py`
- Create: `backend/app/db/models/repository_snapshot.py`
- Create: `backend/alembic/versions/0004_create_pico_online_agent_schema.py`
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/unit/db/test_agent_models_schema.py`

- [ ] **Step 1: Write the failing schema test**

Create `backend/tests/unit/db/test_agent_models_schema.py` with:

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

- [ ] **Step 2: Run the schema test and verify it fails**

Run: `cd backend && pytest tests/unit/db/test_agent_models_schema.py -q`

Expected: FAIL because the agent tables do not exist.

- [ ] **Step 3: Add ORM models**

Create `backend/app/db/models/repository_snapshot.py`:

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

Create the remaining model files with the same `BigIntPrimaryKeyMixin` and `TimestampMixin` style:

```python
# backend/app/db/models/agent_session.py
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, Text, text
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

Use equivalent definitions for `AgentMessage`, `AgentRun`, `AgentRunEvent`, and `AgentArtifact` with the fields from the approved spec.

- [ ] **Step 4: Export models**

Modify `backend/app/db/models/__init__.py` to import and include:

```python
from app.db.models.agent_artifact import AgentArtifact
from app.db.models.agent_message import AgentMessage
from app.db.models.agent_run import AgentRun
from app.db.models.agent_run_event import AgentRunEvent
from app.db.models.agent_session import AgentSession
from app.db.models.repository_snapshot import RepositorySnapshot
```

Add these names to `__all__`.

- [ ] **Step 5: Add Alembic migration**

Create `backend/alembic/versions/0004_create_pico_online_agent_schema.py` using `revision = "0004_pico_online_agent_schema"` and `down_revision = "0003_webhook_review_execution"`. Create the six tables, JSON defaults, foreign keys, and indexes matching the ORM models.

- [ ] **Step 6: Run the schema test**

Run: `cd backend && pytest tests/unit/db/test_agent_models_schema.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/models backend/alembic/versions/0004_create_pico_online_agent_schema.py backend/tests/unit/db/test_agent_models_schema.py
git commit -m "feat: add pico online agent schema"
```

---

### Task 2: Add Pico-Style Memory and Context Core

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/memory.py`
- Create: `backend/app/agent/context.py`
- Create: `backend/app/agent/workspace.py`
- Test: `backend/tests/unit/agent/test_memory_context.py`

- [ ] **Step 1: Write failing memory/context tests**

Create `backend/tests/unit/agent/test_memory_context.py`:

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

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/unit/agent/test_memory_context.py -q`

Expected: FAIL because `app.agent` does not exist.

- [ ] **Step 3: Add memory helper**

Create `backend/app/agent/memory.py` with:

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

- [ ] **Step 4: Add workspace context**

Create `backend/app/agent/workspace.py` with a dataclass that renders the platform workspace prefix and computes a deterministic fingerprint from project/snapshot payload.

- [ ] **Step 5: Add context manager**

Create `backend/app/agent/context.py` with a compact Pico-style context manager that renders `Prefix`, `Memory`, `History`, and `Current user request`, applies section budgets, and returns prompt metadata with rendered section sizes.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/unit/agent/test_memory_context.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent backend/tests/unit/agent/test_memory_context.py
git commit -m "feat: add pico agent context core"
```

---

### Task 3: Implement Read-Only Tool Gateway

**Files:**
- Create: `backend/app/agent/tools.py`
- Create: `backend/app/agent/tool_gateway.py`
- Create: `backend/app/agent/repository_provider.py`
- Test: `backend/tests/unit/agent/test_tool_gateway.py`

- [ ] **Step 1: Write failing tool gateway tests**

Create `backend/tests/unit/agent/test_tool_gateway.py` with tests for:

```text
test_gateway_rejects_unknown_tool: call gateway.execute("missing_tool", {}) and assert ValueError contains "unknown tool".
test_gateway_validates_read_file_line_range: call read_file with start=10,end=1 and assert ValueError contains "invalid line range".
test_gateway_blocks_third_identical_recent_tool_call: seed two identical tool history entries and assert the third matching call returns a blocked result.
test_gateway_reuses_same_run_cache_for_same_snapshot: call read_file twice with the same args and assert provider.read_file is called once.
test_gateway_redacts_secret_like_output_before_returning: fake provider returns "token=sk-secret123456" and gateway output contains "<redacted>".
```

Use a fake provider returning `"token=sk-secret123456"` and assert the returned output contains `"<redacted>"`.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/unit/agent/test_tool_gateway.py -q`

Expected: FAIL because the tool gateway does not exist.

- [ ] **Step 3: Define provider protocol**

Create `backend/app/agent/repository_provider.py` with:

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

- [ ] **Step 4: Define read-only tools and validation**

Create `backend/app/agent/tools.py` with specs for `list_files`, `read_file`, `search`, `get_project_overview`, and `get_recent_commits`. Implement validation for empty paths, invalid line ranges, empty search patterns, and `limit` outside `1..50`.

- [ ] **Step 5: Implement gateway execution chain**

Create `backend/app/agent/tool_gateway.py` implementing:

```text
exists -> validate -> repeated guard -> cache lookup -> execute -> redact -> clip -> cache store -> return
```

Repeated guard must match Pico's current behavior: if the last two tool history events have identical `name` and `args` to the current call, reject it.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/unit/agent/test_tool_gateway.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent/tools.py backend/app/agent/tool_gateway.py backend/app/agent/repository_provider.py backend/tests/unit/agent/test_tool_gateway.py
git commit -m "feat: add read-only agent tool gateway"
```

---

### Task 4: Add Repository Snapshot Service

**Files:**
- Create: `backend/app/agent/snapshot_service.py`
- Test: `backend/tests/unit/agent/test_snapshot_service.py`

- [ ] **Step 1: Write failing snapshot tests**

Create `backend/tests/unit/agent/test_snapshot_service.py` covering:

```text
test_snapshot_service_creates_ready_snapshot_for_project: create a Project and fake provider head_sha="sha1"; assert a ready RepositorySnapshot is committed.
test_snapshot_service_marks_existing_snapshot_stale_when_head_changes: seed a ready snapshot with head_sha="old"; call mark_stale_snapshots with "new"; assert old snapshot status is "stale".
test_snapshot_fingerprint_changes_when_head_sha_changes: call build_fingerprint twice with different head_sha values and assert the hashes differ.
```

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/unit/agent/test_snapshot_service.py -q`

Expected: FAIL because `RepositorySnapshotService` does not exist.

- [ ] **Step 3: Implement snapshot service**

Create `backend/app/agent/snapshot_service.py` with methods:

```python
class RepositorySnapshotService:
    def ensure_ready_snapshot(self, *, project, provider) -> RepositorySnapshot:
        """Create or return a ready snapshot for the project's default branch."""

    def mark_stale_snapshots(self, *, project_id: int, ref: str, new_head_sha: str) -> None:
        """Mark ready snapshots stale when their head sha differs from new_head_sha."""

    def build_fingerprint(self, *, project_id: int, platform_type: str, repo_url: str | None, ref: str, head_sha: str, tool_signature: str, settings_hash: str) -> str:
        """Return a sha256 hash for the snapshot identity payload."""
```

Use provider methods to fetch `head_sha`, `file_tree`, `overview`, and `recent_commits`.

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/agent/test_snapshot_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/snapshot_service.py backend/tests/unit/agent/test_snapshot_service.py
git commit -m "feat: add repository snapshot service"
```

---

### Task 5: Implement Agent Run Service with Fake Model

**Files:**
- Create: `backend/app/agent/run_service.py`
- Create: `backend/app/agent/event_recorder.py`
- Create: `backend/app/services/agent_session_service.py`
- Test: `backend/tests/unit/agent/test_run_service.py`

- [ ] **Step 1: Write failing run service tests**

Create `backend/tests/unit/agent/test_run_service.py` with:

```text
test_run_service_completes_final_answer: fake model returns "Final answer"; assert run.status == "completed" and assistant message contains it.
test_run_service_executes_tool_then_completes: fake model returns a read_file tool envelope then final text; assert one tool_result event exists.
test_run_service_stops_at_step_limit: fake model repeatedly returns a search tool call; set max_steps=1 and assert stop_reason == "step_limit_reached".
test_run_service_persists_updated_memory_state: run completes after reading README.md; assert session.memory_state["working"]["recent_files"] includes README.md.
```

Use a fake model returning one tool call response and then a final answer.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/unit/agent/test_run_service.py -q`

Expected: FAIL because `AgentRunService` does not exist.

- [ ] **Step 3: Implement event recorder**

Create `backend/app/agent/event_recorder.py` with:

```python
class AgentEventRecorder:
    def record(self, *, run_id: int, session_id: int, event_type: str, payload: dict) -> None:
        """Persist an AgentRunEvent with the next sequence for this run."""

    def list_after(self, *, session_id: int, after_id: int | None = None) -> list[AgentRunEvent]:
        """Return session events with id greater than after_id ordered by id."""
```

- [ ] **Step 4: Implement session persistence service**

Create `backend/app/services/agent_session_service.py` with methods for creating sessions, messages, runs, and updating assistant messages after completion.

- [ ] **Step 5: Implement run service**

Create `backend/app/agent/run_service.py` with a bounded loop:

```text
load run -> build context -> call fake/model client -> parse final or tool -> execute gateway -> record events -> update message/run/memory
```

Use a simple JSON tool-call envelope for first implementation:

```json
{"tool": {"name": "read_file", "args": {"path": "README.md", "start": 1, "end": 20}}}
```

Treat any non-tool text response as final answer.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/unit/agent/test_run_service.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent/run_service.py backend/app/agent/event_recorder.py backend/app/services/agent_session_service.py backend/tests/unit/agent/test_run_service.py
git commit -m "feat: add pico-style agent run service"
```

---

### Task 6: Add Agent API and SSE

**Files:**
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/api/routes/agent.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/integration/test_agent_api.py`
- Test: `backend/tests/integration/test_agent_sse.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/integration/test_agent_api.py` covering:

```text
test_agent_session_message_and_run_flow: create a project, POST a session, POST a message, assert user_message_id, assistant_message_id, and run_id are integers.
test_agent_endpoints_require_project_read_permission: unauthenticated or limited client receives 403 for session list and message create routes.
test_agent_snapshot_refresh_requires_project_update_permission: user with only project:read receives 403 for snapshot refresh.
```

- [ ] **Step 2: Write failing SSE test**

Create `backend/tests/integration/test_agent_sse.py` covering `GET /api/v1/agent/sessions/{session_id}/stream?since_event_id=0` returning SSE formatted lines for existing events.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

Expected: FAIL because routes do not exist.

- [ ] **Step 4: Add schemas**

Create `backend/app/schemas/agent.py` with request/response models:

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

- [ ] **Step 5: Add routes**

Create `backend/app/api/routes/agent.py` implementing the approved routes:

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

Wire read routes and message creation to `require_permission("project:read")`; wire refresh to `require_permission("project:update")`.

- [ ] **Step 6: Include router**

Modify `backend/app/api/router.py`:

```python
from app.api.routes.agent import router as agent_router

api_router.include_router(agent_router)
```

- [ ] **Step 7: Run API/SSE tests**

Run: `cd backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/agent.py backend/app/api/routes/agent.py backend/app/api/router.py backend/tests/integration/test_agent_api.py backend/tests/integration/test_agent_sse.py
git commit -m "feat: add agent api and event stream"
```

---

### Task 7: Add Frontend Repository Assistant Page

**Files:**
- Create: `frontend/src/features/agent/api.ts`
- Create: `frontend/src/pages/projects/ProjectAgentPage.tsx`
- Create: `frontend/src/pages/projects/ProjectAgentPage.test.tsx`
- Modify: `frontend/src/routes/router.tsx`
- Modify: `frontend/src/pages/projects/ProjectListPage.tsx`
- Modify: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: Write failing frontend test**

Create `frontend/src/pages/projects/ProjectAgentPage.test.tsx` covering:

```tsx
it("renders sessions, sends a message, and appends streamed assistant text", async () => {
  // mock list/create session, post message, and EventSource events
});
```

- [ ] **Step 2: Run frontend test and verify failure**

Run: `cd frontend && npm test -- ProjectAgentPage.test.tsx --runInBand`

Expected: FAIL because the page and API module do not exist.

- [ ] **Step 3: Add API client**

Create `frontend/src/features/agent/api.ts` with functions:

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

- [ ] **Step 4: Add page component**

Create `frontend/src/pages/projects/ProjectAgentPage.tsx` with:

- Session list.
- Message stream.
- Input form.
- Snapshot status panel.
- Tool event panel.
- EventSource lifecycle cleanup.

- [ ] **Step 5: Wire route and project entry**

Add route `/projects/:projectId/agent` in `frontend/src/routes/router.tsx`. Add an action button/link from `ProjectListPage` rows to that route.

- [ ] **Step 6: Run frontend tests**

Run: `cd frontend && npm test -- ProjectAgentPage.test.tsx --runInBand`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/agent/api.ts frontend/src/pages/projects/ProjectAgentPage.tsx frontend/src/pages/projects/ProjectAgentPage.test.tsx frontend/src/routes/router.tsx frontend/src/pages/projects/ProjectListPage.tsx frontend/src/lib/api/types.ts
git commit -m "feat: add project repository assistant page"
```

---

### Task 8: Run Full Verification and Update Docs

**Files:**
- Modify: `backend/README.md`
- Modify: `README.md`
- Create: `docs/verification/2026-06-03-pico-online-agent-mvp.md`

- [ ] **Step 1: Run backend unit and integration tests**

Run: `cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm test -- --run`

Expected: PASS.

- [ ] **Step 3: Update docs**

Update `README.md` and `backend/README.md` with the new project-level repository assistant capability, route summary, and read-only scope.

- [ ] **Step 4: Write verification note**

Create `docs/verification/2026-06-03-pico-online-agent-mvp.md` with:

```markdown
# Pico Online Agent MVP Verification

## Commands

- `cd backend && pytest tests/unit/agent tests/unit/db/test_agent_models_schema.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
- `cd frontend && npm test -- --run`

## Result

Both backend and frontend verification commands passed.

## Scope Confirmed

- Read-only tools only.
- No shell/write/patch/delegate.
- Session, messages, runs, events, artifacts, and snapshots persist in PostgreSQL.
- SSE stream can replay events.
```

- [ ] **Step 5: Commit**

```bash
git add README.md backend/README.md docs/verification/2026-06-03-pico-online-agent-mvp.md
git commit -m "docs: verify pico online agent mvp"
```

---

## Self-Review

Spec coverage:

- Data model requirements are covered by Task 1.
- Pico context and memory preservation are covered by Task 2.
- Tool existence, validation, repeated-call guard, cache, redaction, clipping, and recording are covered by Task 3.
- Lightweight snapshot and fingerprint strategy are covered by Task 4.
- Multi-step run loop and memory persistence are covered by Task 5.
- API and SSE protocol are covered by Task 6.
- Project-level frontend entry is covered by Task 7.
- Verification and docs are covered by Task 8.

Implementation boundaries:

- The plan keeps shell/write/patch/delegate/checkpoint/resume out of scope.
- The plan keeps full RAG and embedding out of scope.
- The plan uses fake model/provider tests before real provider integration to keep early tasks deterministic.
