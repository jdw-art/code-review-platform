# Full Review Flow Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI verification script that performs one real GitHub `git push`, observes the full review pipeline end-to-end, and writes a markdown report with confirmed passes, failures, and blockers.

**Architecture:** A standalone Python script in `backend/scripts` orchestrates four focused responsibilities: preflight checks, one real test commit/push on a dedicated branch, worker lifecycle management, and multi-source observation across PostgreSQL, Redis, worker logs, and GitHub comments. The script does not modify the production webhook/worker implementation; it only inspects behavior and emits evidence.

**Tech Stack:** Python 3.12, Git CLI, FastAPI backend, PostgreSQL, Redis, pytest, Markdown report generation

---

## File Structure

### New files

- `backend/scripts/verify_full_review_flow.py`
  - CLI entrypoint for the end-to-end verification run.
- `backend/tests/unit/scripts/test_verify_full_review_flow.py`
  - Unit tests for run-id generation, README patching, status classification, and report rendering.
- `backend/tests/integration/test_verify_full_review_flow_smoke.py`
  - Smoke coverage for a no-op / dry-run style invocation path if needed for script wiring.
- `docs/verification/.gitkeep`
  - Keeps the verification output directory present in git.

### Modified files

- `backend/README.md`
  - Add a short note that the verification script exists and is intended for real GitHub push validation.
- `backend/pyproject.toml`
  - Add any standard-library-only or already-available runtime dependencies if the script needs them for tests or CLI ergonomics.
- `backend/tests/unit/test_readme_smoke.py`
  - Lock in README wording if the script notice is added there.

## Task 1: Define the verification script contract and report model

**Files:**
- Create: `backend/scripts/verify_full_review_flow.py`
- Create: `backend/tests/unit/scripts/test_verify_full_review_flow.py`

- [ ] **Step 1: Write the failing test for run-id and branch naming**

```python
from backend.scripts.verify_full_review_flow import build_run_id, build_branch_name


def test_build_run_id_and_branch_name() -> None:
    run_id = build_run_id(prefix="verify/review-flow")
    branch_name = build_branch_name(prefix="verify/review-flow", run_id=run_id)

    assert run_id.startswith("verify-review-flow-")
    assert branch_name == f"verify/review-flow/{run_id}"
```

- [ ] **Step 2: Run the test and confirm it fails before implementation**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: FAIL because the script module does not exist yet.

- [ ] **Step 3: Implement the minimal helpers and report dataclasses**

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def build_run_id(prefix: str) -> str:
    safe_prefix = prefix.strip().replace("/", "-").replace("_", "-")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"{safe_prefix}-{ts}-{suffix}"


def build_branch_name(prefix: str, run_id: str) -> str:
    return f"{prefix.rstrip('/')}/{run_id}"
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the contract layer**

```bash
git add backend/scripts/verify_full_review_flow.py backend/tests/unit/scripts/test_verify_full_review_flow.py
git commit -m "test: add verification flow script contract"
```

## Task 2: Implement preflight checks and README mutation helpers

**Files:**
- Modify: `backend/scripts/verify_full_review_flow.py`
- Test: `backend/tests/unit/scripts/test_verify_full_review_flow.py`

- [ ] **Step 1: Write the failing test for preflight failure reporting**

```python
from backend.scripts.verify_full_review_flow import run_preflight_checks


def test_preflight_reports_missing_required_env(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)
    result = run_preflight_checks(repo_root="/tmp/repo", backend_root="/tmp/backend")

    assert result.ok is False
    assert "GITHUB_ACCESS_TOKEN" in result.errors
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -k preflight -q`
Expected: FAIL because preflight helpers are not implemented yet.

- [ ] **Step 3: Implement preflight, README patching, and restore helpers**

```python
def run_preflight_checks(repo_root: str, backend_root: str) -> PreflightResult:
    # check git, pg, redis, backend health, env, and baseline snapshots
    ...


def patch_readme(readme_path: Path, run_id: str) -> tuple[str, str]:
    original = readme_path.read_text(encoding="utf-8")
    marker = f"<!-- verify:{run_id} -->"
    updated = original.rstrip() + f"\n\n{marker}\n"
    readme_path.write_text(updated, encoding="utf-8")
    return original, updated


def restore_readme(readme_path: Path, original: str) -> None:
    readme_path.write_text(original, encoding="utf-8")
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the preflight layer**

```bash
git add backend/scripts/verify_full_review_flow.py backend/tests/unit/scripts/test_verify_full_review_flow.py
git commit -m "feat: add verification preflight and README patch helpers"
```

## Task 3: Implement worker orchestration and chain observers

**Files:**
- Modify: `backend/scripts/verify_full_review_flow.py`
- Test: `backend/tests/unit/scripts/test_verify_full_review_flow.py`

- [ ] **Step 1: Write the failing test for worker lifecycle wrapping**

```python
from backend.scripts.verify_full_review_flow import WorkerProcessManager


def test_worker_manager_tracks_process_lifecycle() -> None:
    manager = WorkerProcessManager(command=["python", "-m", "app.workers.review_worker"])
    assert manager.is_configured() is True
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -k worker_manager -q`
Expected: FAIL because the manager is not implemented yet.

- [ ] **Step 3: Implement worker process manager and observer snapshots**

```python
class WorkerProcessManager:
    def __init__(self, command: list[str], cwd: Path | None = None) -> None:
        self.command = command
        self.cwd = cwd

    def is_configured(self) -> bool:
        return bool(self.command)


@dataclass
class ObservationSnapshot:
    review_records: list[dict[str, object]] = field(default_factory=list)
    redis_queue_length: int | None = None
    worker_stdout: str = ""
    worker_stderr: str = ""
    github_comment_status: str | None = None
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the orchestration layer**

```bash
git add backend/scripts/verify_full_review_flow.py backend/tests/unit/scripts/test_verify_full_review_flow.py
git commit -m "feat: add verification worker orchestration"
```

## Task 4: Implement database, Redis, and GitHub comment polling

**Files:**
- Modify: `backend/scripts/verify_full_review_flow.py`
- Test: `backend/tests/unit/scripts/test_verify_full_review_flow.py`

- [ ] **Step 1: Write the failing test for status classification**

```python
from backend.scripts.verify_full_review_flow import classify_result


def test_classify_result_distinguishes_core_and_full_pass() -> None:
    assert classify_result(core_pass=True, comment_pass=False) == "核心通过"
    assert classify_result(core_pass=True, comment_pass=True) == "完整通过"
    assert classify_result(core_pass=False, comment_pass=False) == "失败"
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -k classify_result -q`
Expected: FAIL because the classifier is not implemented yet.

- [ ] **Step 3: Implement polling helpers and classification**

```python
def classify_result(core_pass: bool, comment_pass: bool) -> str:
    if not core_pass:
        return "失败"
    if comment_pass:
        return "完整通过"
    return "核心通过"
```

- [ ] **Step 4: Add database and Redis observation helpers**

```python
def fetch_latest_review_records(session, limit: int = 10) -> list[dict[str, object]]:
    ...


def fetch_redis_queue_length(redis_client, queue_name: str) -> int:
    ...
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: PASS.

- [ ] **Step 6: Commit the observer layer**

```bash
git add backend/scripts/verify_full_review_flow.py backend/tests/unit/scripts/test_verify_full_review_flow.py
git commit -m "feat: add verification observers and result classification"
```

## Task 5: Implement markdown report rendering and CLI wiring

**Files:**
- Modify: `backend/scripts/verify_full_review_flow.py`
- Test: `backend/tests/unit/scripts/test_verify_full_review_flow.py`
- Create: `docs/verification/.gitkeep`
- Modify: `backend/README.md`

- [ ] **Step 1: Write the failing test for markdown rendering**

```python
from backend.scripts.verify_full_review_flow import render_report


def test_render_report_includes_pass_fail_and_blockers() -> None:
    markdown = render_report(
        run_id="verify-review-flow-20260101010101-abc12345",
        conclusion="核心通过",
        passed_items=["review_record 新增", "review_status 流转"],
        failed_items=["GitHub comment 未确认"],
        blockers=["Redis 队列已空，当前任务可能已被旧 worker 消费"],
    )

    assert "核心通过" in markdown
    assert "GitHub comment 未确认" in markdown
    assert "Redis 队列已空" in markdown
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -k render_report -q`
Expected: FAIL because the renderer is not implemented yet.

- [ ] **Step 3: Implement Markdown rendering and CLI main**

```python
def render_report(...):
    return "\n".join([...])


def main(argv: list[str] | None = None) -> int:
    # parse args, run preflight, start worker, trigger push, observe, write report
    ...
```

- [ ] **Step 4: Add verification docs directory marker and README note**

```bash
mkdir -p docs/verification
touch docs/verification/.gitkeep
```

```markdown
## Verification

Use `python scripts/verify_full_review_flow.py` to run a real GitHub push-based end-to-end validation of the review pipeline.
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_verify_full_review_flow.py -q`
Expected: PASS.

- [ ] **Step 6: Commit the CLI and report layer**

```bash
git add backend/scripts/verify_full_review_flow.py backend/tests/unit/scripts/test_verify_full_review_flow.py backend/README.md docs/verification/.gitkeep
git commit -m "feat: add full review flow verification cli"
```

## Task 6: Smoke-test the script contract

**Files:**
- Modify: `backend/tests/integration/test_verify_full_review_flow_smoke.py`

- [ ] **Step 1: Write a smoke test that imports the CLI module**

```python
def test_verify_full_review_flow_module_imports() -> None:
    import backend.scripts.verify_full_review_flow  # noqa: F401
```

- [ ] **Step 2: Run the smoke test**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_verify_full_review_flow_smoke.py -q`
Expected: PASS.

- [ ] **Step 3: Commit the smoke test**

```bash
git add backend/tests/integration/test_verify_full_review_flow_smoke.py
git commit -m "test: add verification script smoke coverage"
```

## Task 7: Document how to use the verifier

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: Add a concise README section for the verification script**

```markdown
## Verification Script

Run `python scripts/verify_full_review_flow.py` from `backend/` to perform a real GitHub push-based end-to-end validation of the review pipeline. The script auto-launches `review_worker`, keeps the test branch and commit, and writes a markdown report under `docs/verification/`.
```

- [ ] **Step 2: Run README smoke tests**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/test_readme_smoke.py -q`
Expected: PASS.

- [ ] **Step 3: Commit the README update**

```bash
git add backend/README.md backend/tests/unit/test_readme_smoke.py
git commit -m "docs: document review flow verification script"
```

## Verification Strategy

- Unit-test all helper functions before touching the CLI entrypoint.
- Keep each task limited to one responsibility.
- Use real `git push` only in the manual validation run after the script is implemented.
- Preserve test branch and commit to keep evidence intact.
- Collect stdout/stderr and database snapshots even when a stage fails.

## Execution Notes

- The plan intentionally does not modify production review or webhook behavior.
- The first real end-to-end run should be performed manually after the script is finished, because it requires live GitHub, Redis, PostgreSQL, and an already-running FastAPI backend.
- If the manual run exposes stale queued records or comment permission issues, record them in the generated verification report rather than silently compensating in code.
