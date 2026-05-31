# Backend 单入口与 CodeReview 全量迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `backend` 在本地开发模式下只需启动 `uvicorn` 即可自动托管 review worker，并将 `codereview/` 中仍在使用的 reviewer、prompt、reporter 核心能力迁入 `backend`，最终删除 `codereview/` 目录。

**Architecture:** 保留现有 `app/integrations/*`、`ReviewExecutionService`、`DailyReportService`、`review_worker.py` 等 backend 已有主干，只新增一个开发态 `DevWorkerSupervisor` 和一组 `app/review/*` 核心模块。迁移过程中通过 `ReviewerProtocol + Legacy/Backend` 双实现开关保持真实链路可回退，优先把 `prompt_templates.yml` 的现有行为等价迁入，再切换默认 reviewer。

**Tech Stack:** FastAPI lifespan, Python multiprocessing/subprocess, Pydantic Settings, SQLAlchemy, Redis, pytest, Jinja2, YAML, existing GitHub/GitLab integration adapters

---

## Acceptance Gate

本计划的“完成”不以单元测试或集成测试通过为唯一标准，还必须满足以下真实链路验收门槛：

- 必须执行既有真实全链路验证脚本 [verify_full_review_flow.py](/Users/jacob/GitProject/ai-code-reviewer/backend/scripts/verify_full_review_flow.py)。
- 验证方式以既有计划 [2026-05-31-full-review-flow-verification-plan.md](/Users/jacob/GitProject/ai-code-reviewer/docs/superpowers/plans/2026-05-31-full-review-flow-verification-plan.md) 为准，不重新发明新的验收口径。
- 验证产物必须落到 `docs/verification/`，形成新的现场报告，而不是只口头说明“已跑过”。
- 至少达到 `核心通过`；若 comment 与通知链路也正常，则以 `完整通过` 为目标。
- 只有在真实链路验收通过后，才允许删除 `codereview/` 并宣告迁移完成。

## File Structure

### New files

- `backend/app/workers/dev_worker_supervisor.py`
  - 开发态 worker 子进程托管、健康检查、优雅退出。
- `backend/app/review/__init__.py`
  - review 核心模块导出。
- `backend/app/review/llm/__init__.py`
  - LLM 相关能力导出。
- `backend/app/review/llm/provider.py`
  - 从 backend 配置与兼容环境变量解析 provider、base URL、model 等 reviewer 运行参数。
- `backend/app/review/reviewer/__init__.py`
  - reviewer 相关导出。
- `backend/app/review/reviewer/protocol.py`
  - `ReviewerProtocol`、`ReviewRequest`、`ReviewResult` 等 reviewer 契约。
- `backend/app/review/reviewer/prompt_builder.py`
  - 保留 `prompt_templates.yml` 语义的 prompt 组装器。
- `backend/app/review/reviewer/prompt_templates.yml`
  - 从 `codereview/conf/prompt_templates.yml` 迁入的兼容 prompt 基线。
- `backend/app/review/reviewer/backend_reviewer.py`
  - backend 原生 reviewer，实现 prompt 组装、LLM 调用、分数解析。
- `backend/app/review/reviewer/legacy_reviewer.py`
  - 承载旧 `codereview` bridge 逻辑，作为迁移期回退实现。
- `backend/app/review/reviewer/factory.py`
  - 根据配置返回 legacy 或 backend reviewer。
- `backend/app/review/reporting/__init__.py`
  - reporting 能力导出。
- `backend/app/review/reporting/daily_report_renderer.py`
  - 从 `codereview` 迁入的日报文本生成逻辑。
- `backend/tests/unit/workers/test_dev_worker_supervisor.py`
  - 开发态 worker 托管单测。
- `backend/tests/unit/review/test_prompt_builder.py`
  - prompt 模板兼容性单测。
- `backend/tests/unit/review/test_backend_reviewer.py`
  - backend reviewer 单测。
- `backend/tests/unit/review/test_reviewer_factory.py`
  - reviewer 工厂与开关单测。
- `backend/tests/unit/review/test_daily_report_renderer.py`
  - 日报 renderer 单测。
- `backend/tests/integration/test_dev_autostart_worker.py`
  - 本地单入口生命周期集成测试。
- `backend/tests/integration/test_backend_reviewer_flow.py`
  - backend reviewer 接入现有执行流后的集成测试。

### Modified files

- `backend/app/core/config.py`
  - 新增开发态自动拉起 worker 与 backend reviewer 切换开关。
- `backend/app/main.py`
  - 在现有 `lifespan` 中托管开发态 worker supervisor。
- `backend/app/workers/review_worker.py`
  - 去除 reviewer 细节内嵌，改为复用 `app/review/*` 工厂与实现。
- `backend/app/services/review_execution_service.py`
  - 收口 reviewer 输入/输出契约，减少对旧 bridge 结构的耦合。
- `backend/app/services/daily_report_service.py`
  - 改为依赖 backend 内部 renderer，而不是直接 import `codereview` reporter。
- `backend/tests/unit/test_review_worker_smoke.py`
  - 跟进 worker 入口和 factory 行为。
- `backend/tests/unit/test_main_warning_smoke.py`
  - 跟进 lifespan 新行为。
- `backend/tests/integration/test_review_worker_flow.py`
  - 跟进 reviewer 切换与本地 worker 生命周期。
- `backend/tests/integration/test_daily_report_service.py`
  - 跟进 backend report renderer。
- `backend/README.md`
  - 补充开发态单入口启动方式与迁移后的运行说明。

### Existing acceptance artifacts

- `docs/superpowers/plans/2026-05-31-full-review-flow-verification-plan.md`
  - 真实链路验证脚本的既有验收计划，作为本计划的正式验收依据之一。
- `backend/scripts/verify_full_review_flow.py`
  - 已存在的真实 GitHub `git push` 全链路验证脚本，作为迁移完成前必须执行的验收脚本。
- `docs/verification/2026-05-31-real-flow-run-01.md`
  - 既有现场报告样例，可作为新报告结构和证据粒度参考。
- `docs/verification/2026-05-31-real-flow-run-02.md`
  - 既有现场报告样例，可作为新报告结构和证据粒度参考。
- `docs/verification/2026-05-31-real-flow-run-03.md`
  - 既有现场报告样例，可作为新报告结构和证据粒度参考。

### Delete later

- `codereview/conf/prompt_templates.yml`
- `codereview/biz/utils/code_reviewer.py`
- `codereview/biz/utils/reporter.py`
- `codereview/` 目录下其余仅为 backend 迁移服务的运行时代码

说明：删除动作只在最后一个任务执行，并以真实链路验证通过为前提。

## Task 1: 增加开发态自动托管 worker 的配置开关和 supervisor

**Files:**
- Create: `backend/app/workers/dev_worker_supervisor.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/unit/workers/test_dev_worker_supervisor.py`
- Test: `backend/tests/unit/test_config_smoke.py`

- [ ] **Step 1: 先为配置项写失败测试**

```python
from app.core.config import Settings


def test_settings_exposes_dev_worker_flags(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1",
                "AI_CODE_REVIEWER_USE_BACKEND_REVIEWER=0",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(Settings, "model_config", Settings.model_config.copy(update={"env_file": env_file}))

    settings = Settings()

    assert settings.dev_autostart_worker is True
    assert settings.use_backend_reviewer is False
```

- [ ] **Step 2: 运行配置测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/test_config_smoke.py -k dev_worker_flags -v`
Expected: FAIL with missing settings fields.

- [ ] **Step 3: 为 supervisor 写失败测试**

```python
from pathlib import Path

from app.workers.dev_worker_supervisor import DevWorkerSupervisor


def test_supervisor_builds_worker_command() -> None:
    supervisor = DevWorkerSupervisor(
        backend_dir=Path("/tmp/backend"),
        python_executable="/usr/bin/python3",
    )

    assert supervisor.build_command() == [
        "/usr/bin/python3",
        "-m",
        "app.workers.review_worker",
    ]
```

- [ ] **Step 4: 运行 supervisor 测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/workers/test_dev_worker_supervisor.py -v`
Expected: FAIL because `dev_worker_supervisor.py` does not exist yet.

- [ ] **Step 5: 在配置中新增开发态与 reviewer 切换开关**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="AI_CODE_REVIEWER_",
        extra="ignore",
    )

    dev_autostart_worker: bool = False
    use_backend_reviewer: bool = False
```

- [ ] **Step 6: 实现最小可用的 worker supervisor**

```python
from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


class DevWorkerSupervisor:
    def __init__(self, *, backend_dir: Path, python_executable: str) -> None:
        self.backend_dir = backend_dir
        self.python_executable = python_executable
        self.process: subprocess.Popen[str] | None = None

    def build_command(self) -> list[str]:
        return [self.python_executable, "-m", "app.workers.review_worker"]

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        self.process = subprocess.Popen(
            self.build_command(),
            cwd=self.backend_dir,
            text=True,
            env={**os.environ, "AI_CODE_REVIEWER_MANAGED_BY_SUPERVISOR": "1"},
        )

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.send_signal(signal.SIGTERM)
        self.process.wait(timeout=10)
```

- [ ] **Step 7: 运行新增单测确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/workers/test_dev_worker_supervisor.py tests/unit/test_config_smoke.py -v`
Expected: PASS with new settings and supervisor tests green.

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/core/config.py \
  backend/app/workers/dev_worker_supervisor.py \
  backend/tests/unit/workers/test_dev_worker_supervisor.py \
  backend/tests/unit/test_config_smoke.py
git commit -m "feat: add dev worker supervisor settings"
```

## Task 2: 将开发态 worker supervisor 接入现有 FastAPI lifespan

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/unit/test_main_warning_smoke.py`
- Test: `backend/tests/integration/test_dev_autostart_worker.py`

- [ ] **Step 1: 先为 lifespan 托管行为写失败测试**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI


async def test_lifespan_starts_supervisor_when_enabled(monkeypatch) -> None:
    events: list[str] = []

    class FakeSupervisor:
        def start(self) -> None:
            events.append("start")

        def stop(self) -> None:
            events.append("stop")

    monkeypatch.setattr("app.main.DevWorkerSupervisor", lambda **_: FakeSupervisor())
    monkeypatch.setattr("app.main.settings.dev_autostart_worker", True)

    from app.main import lifespan

    app = FastAPI()
    async with lifespan(app):
        assert events == ["start"]

    assert events == ["start", "stop"]
```

- [ ] **Step 2: 运行生命周期测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/test_main_warning_smoke.py -k starts_supervisor -v`
Expected: FAIL with missing supervisor lifecycle hooks.

- [ ] **Step 3: 在 `main.py` 中接入 supervisor**

```python
from app.workers.dev_worker_supervisor import DevWorkerSupervisor


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    supervisor: DevWorkerSupervisor | None = None
    if settings.dev_autostart_worker:
        supervisor = DevWorkerSupervisor(
            backend_dir=BACKEND_DIR,
            python_executable=sys.executable,
        )
        supervisor.start()
    await run_bootstrap()
    try:
        yield
    finally:
        if supervisor is not None:
            supervisor.stop()
```

- [ ] **Step 4: 增加一个轻量集成测试，验证关闭开关时不启动**

```python
def test_lifespan_skips_supervisor_when_flag_disabled(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSupervisor:
        def __init__(self, **_: object) -> None:
            calls.append("init")

    monkeypatch.setattr("app.main.DevWorkerSupervisor", FakeSupervisor)
    monkeypatch.setattr("app.main.settings.dev_autostart_worker", False)

    from app.main import lifespan

    app = FastAPI()
    async with lifespan(app):
        pass

    assert calls == []
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/test_main_warning_smoke.py tests/integration/test_dev_autostart_worker.py -v`
Expected: PASS with start/stop hooks verified.

- [ ] **Step 6: 提交这一组变更**

```bash
git add backend/app/main.py \
  backend/tests/unit/test_main_warning_smoke.py \
  backend/tests/integration/test_dev_autostart_worker.py
git commit -m "feat: autostart review worker in development lifespan"
```

## Task 3: 抽象 reviewer 协议并把 legacy bridge 从 worker 入口中移出

**Files:**
- Create: `backend/app/review/__init__.py`
- Create: `backend/app/review/reviewer/__init__.py`
- Create: `backend/app/review/reviewer/protocol.py`
- Create: `backend/app/review/reviewer/legacy_reviewer.py`
- Create: `backend/app/review/reviewer/factory.py`
- Modify: `backend/app/workers/review_worker.py`
- Test: `backend/tests/unit/review/test_reviewer_factory.py`
- Test: `backend/tests/unit/test_review_worker_smoke.py`

- [ ] **Step 1: 先为 reviewer 工厂写失败测试**

```python
from app.review.reviewer.factory import build_reviewer


def test_build_reviewer_returns_legacy_when_backend_flag_disabled() -> None:
    reviewer = build_reviewer(use_backend_reviewer=False)
    assert reviewer.__class__.__name__ == "LegacyCodeReviewerAdapter"
```

- [ ] **Step 2: 运行 reviewer 工厂测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_reviewer_factory.py -v`
Expected: FAIL because reviewer factory modules do not exist yet.

- [ ] **Step 3: 建立 reviewer 协议文件**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ReviewRequest:
    record: Any
    changes: list[dict[str, Any]]
    commits: list[dict[str, Any]]


class ReviewerProtocol(Protocol):
    def review(self, request: ReviewRequest) -> str: ...

    def parse_score(self, review_text: str) -> int: ...
```

- [ ] **Step 4: 将现有 legacy bridge 抽到独立文件**

```python
class LegacyCodeReviewerAdapter:
    def __init__(self) -> None:
        _ensure_codereview_on_path()
        from biz.utils.code_reviewer import CodeReviewer

        self._reviewer = CodeReviewer()

    def review(self, request: ReviewRequest) -> str:
        commits_text = ";".join(
            str(item.get("message")).strip()
            for item in request.commits
            if item.get("message")
        )
        return self._reviewer.review_and_strip_code(str(request.changes), commits_text)

    def parse_score(self, review_text: str) -> int:
        return self._reviewer.parse_review_score(review_text)
```

- [ ] **Step 5: 实现 reviewer 工厂**

```python
from app.review.reviewer.legacy_reviewer import LegacyCodeReviewerAdapter


def build_reviewer(*, use_backend_reviewer: bool) -> ReviewerProtocol:
    if use_backend_reviewer:
        from app.review.reviewer.backend_reviewer import BackendCodeReviewer

        return BackendCodeReviewer()
    return LegacyCodeReviewerAdapter()
```

- [ ] **Step 6: 修改 `review_worker.py` 只保留队列与执行入口**

```python
from app.review.reviewer.factory import build_reviewer


def build_review_execution_service(*, session) -> ReviewExecutionService:
    return ReviewExecutionService(
        session=session,
        adapter_registry=IntegrationAdapterRegistry(),
        reviewer=build_reviewer(use_backend_reviewer=get_settings().use_backend_reviewer),
        comment_service=ReviewCommentService(),
        notification_service=ReviewNotificationService(),
    )
```

- [ ] **Step 7: 运行相关单测确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_reviewer_factory.py tests/unit/test_review_worker_smoke.py -v`
Expected: PASS with reviewer factory and worker smoke green.

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/review/__init__.py \
  backend/app/review/reviewer/__init__.py \
  backend/app/review/reviewer/protocol.py \
  backend/app/review/reviewer/legacy_reviewer.py \
  backend/app/review/reviewer/factory.py \
  backend/app/workers/review_worker.py \
  backend/tests/unit/review/test_reviewer_factory.py \
  backend/tests/unit/test_review_worker_smoke.py
git commit -m "refactor: extract reviewer protocol and legacy bridge"
```

## Task 4: 将 `prompt_templates.yml` 和现有 prompt 组装语义兼容迁入 backend

**Files:**
- Create: `backend/app/review/reviewer/prompt_templates.yml`
- Create: `backend/app/review/reviewer/prompt_builder.py`
- Test: `backend/tests/unit/review/test_prompt_builder.py`

- [ ] **Step 1: 先为 prompt 兼容行为写失败测试**

```python
from app.review.reviewer.prompt_builder import ReviewPromptBuilder


def test_prompt_builder_renders_style_diffs_and_commits() -> None:
    builder = ReviewPromptBuilder()
    messages = builder.build_messages(
        style="gentle",
        diffs_text="diff --git a.py b.py",
        commits_text="feat: add login",
    )

    assert messages[0]["role"] == "system"
    assert "gentle" in messages[0]["content"]
    assert "diff --git a.py b.py" in messages[1]["content"]
    assert "feat: add login" in messages[1]["content"]
```

- [ ] **Step 2: 运行 prompt builder 测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_prompt_builder.py -v`
Expected: FAIL because prompt builder and local YAML file do not exist yet.

- [ ] **Step 3: 迁入 `prompt_templates.yml`**

```yaml
code_review_prompt:
  system_prompt: |-
    你是一位资深的软件开发工程师，专注于代码的规范性、功能性、安全性和稳定性。
    整个评论要保持{{ style }}风格
  user_prompt: |-
    以下是某位员工向 GitLab 代码库提交的代码，请以{{ style }}风格审查以下代码。

    代码变更内容：
    {diffs_text}

    提交历史(commits)：
    {commits_text}
```

- [ ] **Step 4: 实现兼容 prompt builder**

```python
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template


class ReviewPromptBuilder:
    def __init__(self, template_path: Path | None = None) -> None:
        self.template_path = template_path or Path(__file__).with_name("prompt_templates.yml")

    def build_messages(self, *, style: str, diffs_text: str, commits_text: str) -> list[dict[str, str]]:
        prompts = yaml.safe_load(self.template_path.read_text(encoding="utf-8"))["code_review_prompt"]
        system_prompt = Template(prompts["system_prompt"]).render(style=style)
        user_prompt_template = Template(prompts["user_prompt"]).render(style=style)
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt_template.format(
                    diffs_text=diffs_text,
                    commits_text=commits_text,
                ),
            },
        ]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_prompt_builder.py -v`
Expected: PASS with equivalent prompt rendering semantics.

- [ ] **Step 6: 提交这一组变更**

```bash
git add backend/app/review/reviewer/prompt_templates.yml \
  backend/app/review/reviewer/prompt_builder.py \
  backend/tests/unit/review/test_prompt_builder.py
git commit -m "feat: migrate prompt template compatibility into backend"
```

## Task 5: 实现 backend 原生 reviewer 并保留旧环境变量行为

**Files:**
- Create: `backend/app/review/llm/__init__.py`
- Create: `backend/app/review/llm/provider.py`
- Create: `backend/app/review/reviewer/backend_reviewer.py`
- Modify: `backend/app/services/review_execution_service.py`
- Test: `backend/tests/unit/review/test_backend_reviewer.py`
- Test: `backend/tests/unit/services/test_review_execution_service.py`

- [ ] **Step 1: 先为 backend reviewer 写失败测试**

```python
from app.review.reviewer.backend_reviewer import BackendCodeReviewer


def test_backend_reviewer_parses_score_from_review_text() -> None:
    reviewer = BackendCodeReviewer(client=None)

    assert reviewer.parse_score("总分:88分") == 88
    assert reviewer.parse_score("未给出评分") == 0
```

- [ ] **Step 2: 运行 reviewer 测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_backend_reviewer.py -v`
Expected: FAIL because `BackendCodeReviewer` does not exist yet.

- [ ] **Step 3: 实现 LLM provider 配置解析**

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class ReviewerLLMConfig:
    provider: str
    api_key: str | None
    api_base_url: str | None
    model: str | None


def load_reviewer_llm_config() -> ReviewerLLMConfig:
    return ReviewerLLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base_url=os.getenv("OPENAI_API_BASE_URL"),
        model=os.getenv("OPENAI_API_MODEL"),
    )
```

- [ ] **Step 4: 实现 backend reviewer 最小版本**

```python
from __future__ import annotations

import re
from typing import Any

from app.review.reviewer.prompt_builder import ReviewPromptBuilder
from app.review.reviewer.protocol import ReviewRequest


class BackendCodeReviewer:
    def __init__(self, *, client: Any | None = None, prompt_builder: ReviewPromptBuilder | None = None) -> None:
        self.client = client
        self.prompt_builder = prompt_builder or ReviewPromptBuilder()

    def review(self, request: ReviewRequest) -> str:
        commits_text = ";".join(
            str(item.get("message")).strip()
            for item in request.commits
            if item.get("message")
        )
        messages = self.prompt_builder.build_messages(
            style=os.getenv("REVIEW_STYLE", "professional"),
            diffs_text=str(request.changes),
            commits_text=commits_text,
        )
        if self.client is None:
            raise RuntimeError("LLM client is not configured")
        return self.client.completions(messages=messages).strip()

    @staticmethod
    def parse_score(review_text: str) -> int:
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text or "")
        return int(match.group(1)) if match else 0
```

- [ ] **Step 5: 调整执行服务改用 `ReviewRequest`**

```python
from app.review.reviewer.protocol import ReviewRequest


review_text = self.reviewer.review(
    ReviewRequest(
        record=record,
        changes=filtered_changes,
        commits=commits,
    )
)
```

- [ ] **Step 6: 运行 reviewer 与执行服务测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_backend_reviewer.py tests/unit/services/test_review_execution_service.py -v`
Expected: PASS with backend reviewer score parsing and execution service contract green.

- [ ] **Step 7: 提交这一组变更**

```bash
git add backend/app/review/llm/__init__.py \
  backend/app/review/llm/provider.py \
  backend/app/review/reviewer/backend_reviewer.py \
  backend/app/services/review_execution_service.py \
  backend/tests/unit/review/test_backend_reviewer.py \
  backend/tests/unit/services/test_review_execution_service.py
git commit -m "feat: add backend native reviewer implementation"
```

## Task 6: 将日报文本生成逻辑迁入 backend，并保留 `DailyReportService` 作为编排入口

**Files:**
- Create: `backend/app/review/reporting/__init__.py`
- Create: `backend/app/review/reporting/daily_report_renderer.py`
- Modify: `backend/app/services/daily_report_service.py`
- Test: `backend/tests/unit/review/test_daily_report_renderer.py`
- Test: `backend/tests/integration/test_daily_report_service.py`

- [ ] **Step 1: 先为日报 renderer 写失败测试**

```python
from app.review.reporting.daily_report_renderer import DailyReportRenderer


def test_daily_report_renderer_formats_rows() -> None:
    renderer = DailyReportRenderer()

    report = renderer.generate_report(
        [
            {
                "author": "alice",
                "commit_messages": ["feat: add login"],
                "review_result": "总分:90分",
                "score": 90,
                "project_name": "Portal",
                "updated_at": 1710000000,
            }
        ]
    )

    assert "alice" in report
    assert "Portal" in report
    assert "总分:90分" in report
```

- [ ] **Step 2: 运行 renderer 测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_daily_report_renderer.py -v`
Expected: FAIL because backend report renderer does not exist yet.

- [ ] **Step 3: 从旧 reporter 迁入一个 backend 内 renderer**

```python
class DailyReportRenderer:
    def generate_report(self, rows: list[dict[str, object]]) -> str:
        sections: list[str] = ["# 代码提交日报"]
        for row in rows:
            sections.append(f"## {row['author']} - {row['project_name']}")
            for message in row["commit_messages"]:
                sections.append(f"- {message}")
            if row.get("review_result"):
                sections.append(str(row["review_result"]))
        return "\n".join(sections).strip()
```

- [ ] **Step 4: 修改 `DailyReportService` 改用 backend renderer**

```python
from app.review.reporting.daily_report_renderer import DailyReportRenderer


class DailyReportService:
    def send_today_report(self) -> str | None:
        rows = self.collect_today_rows()
        if not rows:
            return None

        renderer = self.reporter or DailyReportRenderer()
        report_content = renderer.generate_report(rows)
        self.sender.send_env_fallback(
            content=report_content,
            title="代码提交日报",
            project_name=None,
            url_slug=None,
            webhook_data={},
        )
        return report_content
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_daily_report_renderer.py tests/integration/test_daily_report_service.py -v`
Expected: PASS with backend renderer replacing legacy reporter import.

- [ ] **Step 6: 提交这一组变更**

```bash
git add backend/app/review/reporting/__init__.py \
  backend/app/review/reporting/daily_report_renderer.py \
  backend/app/services/daily_report_service.py \
  backend/tests/unit/review/test_daily_report_renderer.py \
  backend/tests/integration/test_daily_report_service.py
git commit -m "feat: migrate daily report renderer into backend"
```

## Task 7: 切换到 backend reviewer 路径并覆盖现有链路测试

**Files:**
- Modify: `backend/app/review/reviewer/factory.py`
- Modify: `backend/app/workers/review_worker.py`
- Modify: `backend/tests/integration/test_review_worker_flow.py`
- Create: `backend/tests/integration/test_backend_reviewer_flow.py`
- Modify: `backend/README.md`

- [ ] **Step 1: 先为 backend reviewer 切换写失败测试**

```python
from app.review.reviewer.factory import build_reviewer


def test_build_reviewer_returns_backend_when_flag_enabled() -> None:
    reviewer = build_reviewer(use_backend_reviewer=True)
    assert reviewer.__class__.__name__ == "BackendCodeReviewer"
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_reviewer_factory.py -k backend_when_flag_enabled -v`
Expected: FAIL until backend reviewer import path and factory wiring are complete.

- [ ] **Step 3: 更新工厂和文档，默认推荐打开 backend reviewer**

```python
def build_reviewer(*, use_backend_reviewer: bool) -> ReviewerProtocol:
    if use_backend_reviewer:
        from app.review.reviewer.backend_reviewer import BackendCodeReviewer

        return BackendCodeReviewer(client=build_llm_client())
    return LegacyCodeReviewerAdapter()
```

```md
## Development

```bash
cd backend
uvicorn app.main:app --reload
```

设置 `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1` 后，本地会自动拉起 review worker。
设置 `AI_CODE_REVIEWER_USE_BACKEND_REVIEWER=1` 后，本地会改用 backend 原生 reviewer。
```

- [ ] **Step 4: 增加一条集成测试覆盖 backend reviewer 流程**

```python
def test_review_worker_flow_with_backend_reviewer(
    monkeypatch,
    session,
    queued_review_record,
) -> None:
    monkeypatch.setenv("AI_CODE_REVIEWER_USE_BACKEND_REVIEWER", "1")
    service = build_review_execution_service(session=session)

    with pytest.raises(RuntimeError, match="LLM client is not configured"):
        service.execute(review_record_id=queued_review_record.id, attempt=1)
```

- [ ] **Step 5: 运行链路测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_reviewer_factory.py tests/integration/test_review_worker_flow.py tests/integration/test_backend_reviewer_flow.py -v`
Expected: PASS with legacy/backend switch behavior covered.

- [ ] **Step 6: 提交这一组变更**

```bash
git add backend/app/review/reviewer/factory.py \
  backend/app/workers/review_worker.py \
  backend/tests/integration/test_review_worker_flow.py \
  backend/tests/integration/test_backend_reviewer_flow.py \
  backend/README.md
git commit -m "feat: wire backend reviewer into worker flow"
```

## Task 8: 删除 `codereview` 运行时依赖并完成回归验证

**Files:**
- Modify: `backend/app/review/reviewer/legacy_reviewer.py`
- Modify: `backend/app/workers/review_worker.py`
- Modify: `backend/app/services/daily_report_service.py`
- Delete: `codereview/`
- Test: `backend/tests/integration/test_verify_full_review_flow_smoke.py`
- Test: `backend/tests/unit/test_readme_smoke.py`

- [ ] **Step 1: 先增加一个防回归测试，要求 backend 路径不再依赖 `codereview` 工作目录**

```python
from pathlib import Path


def test_backend_reviewer_uses_backend_prompt_template_file() -> None:
    prompt_path = Path("app/review/reviewer/prompt_templates.yml")
    assert prompt_path.exists()
```

- [ ] **Step 2: 运行测试确认当前失败或不完整**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_prompt_builder.py tests/unit/test_readme_smoke.py -v`
Expected: FAIL if any remaining runtime path still depends on `codereview`.

- [ ] **Step 3: 移除 `codereview` 目录引用并删除目录**

```python
def _ensure_codereview_on_path() -> None:
    raise RuntimeError("legacy codereview runtime should not be used after migration")
```

```bash
rm -rf /Users/jacob/GitProject/ai-code-reviewer/codereview
```

- [ ] **Step 4: 运行核心测试集**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/review/test_prompt_builder.py tests/unit/review/test_backend_reviewer.py tests/unit/review/test_daily_report_renderer.py tests/unit/services/test_review_execution_service.py tests/integration/test_dev_autostart_worker.py tests/integration/test_review_worker_flow.py tests/integration/test_daily_report_service.py -v`
Expected: PASS with no import path dependency on `codereview`.

- [ ] **Step 5: 运行真实链路验证**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && python scripts/verify_full_review_flow.py --repo-root /Users/jacob/GitProject/ai-code-reviewer --backend-root /Users/jacob/GitProject/ai-code-reviewer/backend --base-branch codex/backend-single-entry-review-migration --project-id 5`
Expected: 按 [2026-05-31-full-review-flow-verification-plan.md](/Users/jacob/GitProject/ai-code-reviewer/docs/superpowers/plans/2026-05-31-full-review-flow-verification-plan.md) 的口径，在 `docs/verification/` 生成新的现场报告，且分类结果至少为 `核心通过`。

- [ ] **Step 6: 提交删除兼容层后的最终变更**

```bash
git add backend/app/review \
  backend/app/workers \
  backend/app/services \
  backend/tests \
  backend/README.md \
  docs/verification
git commit -m "feat: complete backend reviewer migration and remove codereview"
```

## Self-Review

### Spec coverage

- 开发态单入口：Task 1-2 覆盖配置、supervisor、lifespan 托管。
- 保留生产双角色：Task 2 与 README 更新覆盖运行说明，不改变生产双入口。
- reviewer 抽象与兼容开关：Task 3、Task 5、Task 7 覆盖。
- `prompt_templates.yml` 首期保留：Task 4 明确迁入 backend 并保持兼容。
- `project_template` 暂不替代 prompt 基线：Task 4 与 Task 5 只保留覆盖入口，不重写主来源。
- 日报能力迁移：Task 6 覆盖。
- 删除 `codereview/`：Task 8 覆盖，并以既有全链路验证脚本作为最终验收门槛。

### Placeholder scan

- 本计划未使用 `TODO`、`TBD`、`implement later`、`similar to` 等占位语句。
- 每个任务都列出了具体文件、测试命令、最小代码片段和提交命令。

### Type consistency

- `ReviewerProtocol`、`ReviewRequest`、`BackendCodeReviewer`、`LegacyCodeReviewerAdapter`、`DevWorkerSupervisor` 命名在各任务中保持一致。
- `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER` 与 `AI_CODE_REVIEWER_USE_BACKEND_REVIEWER` 开关命名与 spec 保持一致。
