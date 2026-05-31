# CodeReview FastAPI 集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `codereview/` 的 GitLab / GitHub webhook、审查执行、评论回写、通知、日报和历史导入能力迁入当前 `backend`，统一到 FastAPI + PostgreSQL + Redis + Worker 体系。

**Architecture:** FastAPI 负责 webhook 接收、项目匹配、幂等检查、落库与入队；独立 worker 负责拉取变更、调用 LLM、回写评论、发送通知与更新状态。沿用现有 `review_records` / `review_commits` 作为统一事实模型，并通过兼容层复用 `codereview` 的平台适配与通知逻辑。

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Redis, pytest, codereview compatibility adapters

---

## File Structure

### New files

- `backend/alembic/versions/0003_add_webhook_review_execution_schema.py`
  - 扩展 `review_records`、`projects`，为真实 webhook 与 worker 执行态提供字段。
- `backend/app/schemas/integration_webhook.py`
  - webhook 接收、标准化事件、入队响应模型。
- `backend/app/services/integration_project_locator.py`
  - 根据 `repo_url`、`settings` 与平台 payload 匹配平台内项目。
- `backend/app/services/review_queue_service.py`
  - Redis 队列写入、消费、锁与基础重试元数据。
- `backend/app/services/review_execution_service.py`
  - worker 主执行服务，串起 adapter、LLM、评论回写、通知与状态流转。
- `backend/app/services/review_comment_service.py`
  - 平台评论回写编排。
- `backend/app/services/review_notification_service.py`
  - IM 通知编排，桥接 `notification_bots` 与 `codereview` 环境变量兜底。
- `backend/app/services/daily_report_service.py`
  - 基于 PostgreSQL `review_records` 生成日报内容。
- `backend/app/integrations/base.py`
  - 平台适配统一接口定义。
- `backend/app/integrations/gitlab.py`
  - GitLab webhook 解析、changes/commits 拉取、评论回写。
- `backend/app/integrations/github.py`
  - GitHub webhook 解析、changes/commits 拉取、评论回写。
- `backend/app/integrations/__init__.py`
  - adapter 注册与导出。
- `backend/app/workers/review_worker.py`
  - 独立 worker 进程入口。
- `backend/app/workers/report_worker.py`
  - 日报调度入口。
- `backend/app/api/routes/integration_webhooks.py`
  - GitLab / GitHub webhook 路由。
- `backend/tests/unit/services/test_integration_project_locator.py`
  - 项目匹配单测。
- `backend/tests/unit/services/test_review_queue_service.py`
  - 队列与锁单测。
- `backend/tests/unit/services/test_review_execution_service.py`
  - worker 状态流转与执行编排单测。
- `backend/tests/unit/integrations/test_gitlab_adapter.py`
  - GitLab adapter 单测。
- `backend/tests/unit/integrations/test_github_adapter.py`
  - GitHub adapter 单测。
- `backend/tests/integration/test_integration_webhooks_api.py`
  - webhook API 集成测试。
- `backend/tests/integration/test_review_worker_flow.py`
  - webhook -> queued -> reviewed/skipped/failed 流程测试。
- `backend/tests/integration/test_daily_report_service.py`
  - 日报服务集成测试。

### Modified files

- `backend/app/db/models/review_record.py`
  - 增加平台、执行态、投递态、错误与重试字段。
- `backend/app/db/models/project.py`
  - 明确 `settings` 里的外部仓库匹配字段用法。
- `backend/app/db/models/__init__.py`
  - 导出变更后的模型。
- `backend/app/schemas/review_record.py`
  - 暴露新字段与新状态枚举。
- `backend/app/services/review_record_service.py`
  - 让查询与详情接口返回平台、投递与错误信息。
- `backend/app/services/member_analytics_service.py`
  - 过滤 `skipped/failed` 的统计策略并兼容新状态。
- `backend/app/services/dashboard_service.py`
  - 增加真实审查状态的统计口径。
- `backend/app/api/router.py`
  - 注册 webhook 路由。
- `backend/app/core/config.py`
  - 增加 review queue、worker、日报与兼容配置。
- `backend/scripts/import_review_logs.py`
  - 导入历史 SQLite 记录时映射新字段且不触发外部投递。
- `backend/README.md`
  - 记录 worker、webhook、环境变量和迁移说明。
- `backend/tests/unit/db/test_phase2_models_schema.py`
  - 更新模型结构断言。
- `backend/tests/integration/test_review_records_api.py`
  - 更新新字段与新状态断言。

## Task 1: 扩展数据库结构承载真实 webhook 与执行态

**Files:**
- Create: `backend/alembic/versions/0003_add_webhook_review_execution_schema.py`
- Modify: `backend/app/db/models/review_record.py`
- Modify: `backend/app/db/models/project.py`
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/unit/db/test_phase2_models_schema.py`

- [ ] **Step 1: 先为新字段写数据库结构断言**

```python
def test_review_record_schema_includes_execution_columns() -> None:
    columns = _get_table_columns("review_records")
    assert columns["platform_type"]["type"] == "VARCHAR(32)"
    assert columns["delivery_status"]["type"] == "VARCHAR(32)"
    assert columns["retry_count"]["type"] == "INTEGER"
    assert columns["error_message"]["type"] == "TEXT"
    assert columns["external_project_id"]["type"] == "VARCHAR(255)"
```

- [ ] **Step 2: 运行单测确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/db/test_phase2_models_schema.py -k execution_columns -v`
Expected: FAIL with missing column assertion or missing test setup names

- [ ] **Step 3: 在 ORM 模型中补齐执行态、投递态和外部标识字段**

```python
platform_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
delivery_status: Mapped[str] = mapped_column(
    String(32),
    nullable=False,
    default="pending",
    server_default=text("'pending'"),
)
external_project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
external_merge_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
external_pull_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
external_commit_sha: Mapped[str | None] = mapped_column(String(255), nullable=True)
error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
retry_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default=text("0"),
)
reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: 编写 Alembic 迁移**

```python
op.add_column("review_records", sa.Column("platform_type", sa.String(length=32), nullable=True))
op.add_column(
    "review_records",
    sa.Column(
        "delivery_status",
        sa.String(length=32),
        nullable=False,
        server_default=sa.text("'pending'"),
    ),
)
op.add_column("review_records", sa.Column("external_project_id", sa.String(length=255), nullable=True))
op.add_column("review_records", sa.Column("error_message", sa.Text(), nullable=True))
op.add_column(
    "review_records",
    sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
)
```

- [ ] **Step 5: 为项目 settings 字段补充外部仓库匹配约定注释**

```python
settings: Mapped[dict[str, Any]] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
    server_default=text("'{}'::json"),
    doc="可存 external_repo_full_name、gitlab_project_path、external_project_id 等匹配信息",
)
```

- [ ] **Step 6: 运行模型结构测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/db/test_phase2_models_schema.py -v`
Expected: PASS with new column assertions green

- [ ] **Step 7: 提交这一组变更**

```bash
git add backend/alembic/versions/0003_add_webhook_review_execution_schema.py \
  backend/app/db/models/review_record.py \
  backend/app/db/models/project.py \
  backend/app/db/models/__init__.py \
  backend/tests/unit/db/test_phase2_models_schema.py
git commit -m "feat: extend review record schema for webhook execution"
```

## Task 2: 扩展审查记录 schema 与查询服务

**Files:**
- Modify: `backend/app/schemas/review_record.py`
- Modify: `backend/app/services/review_record_service.py`
- Modify: `backend/tests/integration/test_review_records_api.py`

- [ ] **Step 1: 为列表/详情接口写失败测试，要求返回平台和投递状态字段**

```python
def test_review_records_api_exposes_platform_and_delivery_status(
    authenticated_superuser_client,
    seeded_review_record,
) -> None:
    response = authenticated_superuser_client.get("/api/v1/review-records")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["platform_type"] == "gitlab"
    assert item["delivery_status"] == "delivered"
```

- [ ] **Step 2: 运行集成测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_review_records_api.py -k platform_and_delivery_status -v`
Expected: FAIL with missing response fields

- [ ] **Step 3: 扩展 Pydantic 响应模型**

```python
class ReviewRecordListItemResponse(BaseModel):
    id: int
    project_id: int
    event_type: str
    platform_type: str | None = None
    delivery_status: str
    error_message: str | None = None
    retry_count: int
    reviewed_at: datetime | None = None
    failed_at: datetime | None = None
```

- [ ] **Step 4: 更新查询服务映射逻辑**

```python
return ReviewRecordListItemResponse(
    id=record.id,
    project_id=record.project_id,
    event_type=record.event_type,
    platform_type=record.platform_type,
    external_event_id=record.external_event_id,
    project_name_snapshot=record.project_name_snapshot,
    template_id_snapshot=record.template_id_snapshot,
    template_name_snapshot=record.template_name_snapshot,
    author=record.author,
    title=record.title,
    branch=record.branch,
    source_branch=record.source_branch,
    target_branch=record.target_branch,
    commit_count=record.commit_count,
    commit_messages=record.commit_messages,
    score=record.score,
    review_status=record.review_status,
    review_result=record.review_result,
    summary=record.summary,
    url=record.url,
    url_slug=record.url_slug,
    last_commit_id=record.last_commit_id,
    additions=record.additions,
    deletions=record.deletions,
    delivery_status=record.delivery_status,
    error_message=record.error_message,
    retry_count=record.retry_count,
    reviewed_at=record.reviewed_at,
    failed_at=record.failed_at,
)
```

- [ ] **Step 5: 为筛选项和详情补充新状态断言**

```python
assert detail["delivery_status"] == "delivered"
assert detail["retry_count"] == 0
assert detail["platform_type"] == "gitlab"
```

- [ ] **Step 6: 运行接口测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_review_records_api.py -v`
Expected: PASS with updated schema fields

- [ ] **Step 7: 提交这一组变更**

```bash
git add backend/app/schemas/review_record.py \
  backend/app/services/review_record_service.py \
  backend/tests/integration/test_review_records_api.py
git commit -m "feat: expose webhook execution fields in review records api"
```

## Task 3: 建立项目匹配服务

**Files:**
- Create: `backend/app/services/integration_project_locator.py`
- Test: `backend/tests/unit/services/test_integration_project_locator.py`

- [ ] **Step 1: 先写项目匹配优先级测试**

```python
def test_locator_matches_by_repo_url_first(db_session) -> None:
    project = Project(
        name="Repo URL Project",
        key="repo-url-project",
        platform_type="github",
        repo_url="https://github.com/acme/repo-url-project",
        default_branch="main",
        review_enabled=True,
    )
    db_session.add(project)
    db_session.commit()

    locator = IntegrationProjectLocator(db_session)
    matched = locator.locate(
        platform_type="github",
        repo_url="https://github.com/acme/repo-url-project",
        repo_full_name="acme/ignored",
        external_project_id="999",
    )
    assert matched.id == project.id
```

- [ ] **Step 2: 再写 settings 回退匹配测试**

```python
def test_locator_falls_back_to_settings_full_name(db_session) -> None:
    project = Project(
        name="Full Name Project",
        key="full-name-project",
        platform_type="github",
        repo_url=None,
        default_branch="main",
        review_enabled=True,
        settings={"external_repo_full_name": "acme/full-name-project"},
    )
    db_session.add(project)
    db_session.commit()

    locator = IntegrationProjectLocator(db_session)
    matched = locator.locate(
        platform_type="github",
        repo_url=None,
        repo_full_name="acme/full-name-project",
        external_project_id=None,
    )
    assert matched.id == project.id
```

- [ ] **Step 3: 运行单测确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_integration_project_locator.py -v`
Expected: FAIL with import error for `IntegrationProjectLocator`

- [ ] **Step 4: 实现项目匹配服务**

```python
class IntegrationProjectLocator:
    def __init__(self, session: Session) -> None:
        self.session = session

    def locate(
        self,
        *,
        platform_type: str,
        repo_url: str | None,
        repo_full_name: str | None,
        external_project_id: str | None,
    ) -> Project | None:
        projects = self.session.scalars(
            select(Project).where(Project.platform_type == platform_type, Project.is_active.is_(True))
        ).all()
        for project in projects:
            if repo_url and project.repo_url == repo_url:
                return project
            if repo_full_name and project.settings.get("external_repo_full_name") == repo_full_name:
                return project
            if external_project_id and str(project.settings.get("external_project_id")) == str(external_project_id):
                return project
        return None
```

- [ ] **Step 5: 为匹配歧义补充显式异常测试和实现**

```python
with pytest.raises(DomainConflictError) as exc:
    locator.locate(
        platform_type="gitlab",
        repo_url=None,
        repo_full_name="group/repo",
        external_project_id="42",
    )
assert exc.value.code == "PROJECT_WEBHOOK_AMBIGUOUS"
```

- [ ] **Step 6: 运行单测确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_integration_project_locator.py -v`
Expected: PASS with repo_url、settings 和 ambiguity cases green

- [ ] **Step 7: 提交这一组变更**

```bash
git add backend/app/services/integration_project_locator.py \
  backend/tests/unit/services/test_integration_project_locator.py
git commit -m "feat: add webhook project locator service"
```

## Task 4: 建立 webhook schema 与队列服务

**Files:**
- Create: `backend/app/schemas/integration_webhook.py`
- Create: `backend/app/services/review_queue_service.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/unit/services/test_review_queue_service.py`

- [ ] **Step 1: 先写队列消息序列化测试**

```python
def test_queue_service_pushes_minimal_message(fake_redis) -> None:
    service = ReviewQueueService(redis_client=fake_redis, queue_name="review:jobs")
    service.enqueue(review_record_id=101, platform_type="gitlab", attempt=1)
    assert fake_redis.values["review:jobs"] == [
        '{"review_record_id":101,"platform_type":"gitlab","attempt":1}'
    ]
```

- [ ] **Step 2: 写锁测试，确保同一记录不会重复执行**

```python
def test_queue_service_acquires_processing_lock(fake_redis) -> None:
    service = ReviewQueueService(redis_client=fake_redis, queue_name="review:jobs")
    assert service.acquire_lock(review_record_id=7, ttl_seconds=30) is True
    assert service.acquire_lock(review_record_id=7, ttl_seconds=30) is False
```

- [ ] **Step 3: 运行单测确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_queue_service.py -v`
Expected: FAIL with missing queue service class

- [ ] **Step 4: 增加配置项**

```python
review_queue_name: str = "review:jobs"
review_lock_prefix: str = "review:lock"
review_max_retries: int = 3
review_lock_ttl_seconds: int = 1800
report_crontab_expression: str = "0 18 * * 1-5"
```

- [ ] **Step 5: 实现 webhook 与队列 schema**

```python
class WebhookAcceptedResponse(BaseModel):
    review_record_id: int
    status: Literal["queued", "duplicate", "skipped"]


class ReviewQueueMessage(BaseModel):
    review_record_id: int
    platform_type: Literal["gitlab", "github"]
    attempt: int = 1
```

- [ ] **Step 6: 实现队列服务**

```python
class ReviewQueueService:
    def enqueue(self, *, review_record_id: int, platform_type: str, attempt: int = 1) -> None:
        message = ReviewQueueMessage(
            review_record_id=review_record_id,
            platform_type=platform_type,
            attempt=attempt,
        )
        self.redis.rpush(self.queue_name, message.model_dump_json())
```

- [ ] **Step 7: 运行单测确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_queue_service.py -v`
Expected: PASS with enqueue and lock behaviors green

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/schemas/integration_webhook.py \
  backend/app/services/review_queue_service.py \
  backend/app/core/config.py \
  backend/tests/unit/services/test_review_queue_service.py
git commit -m "feat: add webhook queue service and schemas"
```

## Task 5: 实现 GitLab / GitHub adapter

**Files:**
- Create: `backend/app/integrations/base.py`
- Create: `backend/app/integrations/gitlab.py`
- Create: `backend/app/integrations/github.py`
- Create: `backend/app/integrations/__init__.py`
- Test: `backend/tests/unit/integrations/test_gitlab_adapter.py`
- Test: `backend/tests/unit/integrations/test_github_adapter.py`

- [ ] **Step 1: 先写 GitLab webhook 解析测试**

```python
def test_gitlab_adapter_normalizes_merge_request_event() -> None:
    adapter = GitLabAdapter()
    event = adapter.parse_webhook(
        payload={
            "object_kind": "merge_request",
            "project": {"id": 12, "web_url": "https://gitlab.example.com/group/repo"},
            "user": {"username": "alice"},
            "object_attributes": {
                "iid": 3,
                "source_branch": "feature/x",
                "target_branch": "main",
                "last_commit": {"id": "abc123"},
                "title": "feat: x",
            },
        },
        headers={},
    )
    assert event.platform_type == "gitlab"
    assert event.event_type == "merge_request"
    assert event.author == "alice"
    assert event.last_commit_id == "abc123"
```

- [ ] **Step 2: 写 GitHub pull_request 解析测试**

```python
def test_github_adapter_normalizes_pull_request_event() -> None:
    adapter = GitHubAdapter()
    event = adapter.parse_webhook(
        payload={
            "action": "opened",
            "repository": {"id": 9, "full_name": "acme/repo"},
            "pull_request": {
                "number": 8,
                "title": "feat: api",
                "head": {"ref": "feature/api", "sha": "def456"},
                "base": {"ref": "main"},
                "user": {"login": "bob"},
            },
        },
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert event.platform_type == "github"
    assert event.event_type == "pull_request"
    assert event.author == "bob"
    assert event.last_commit_id == "def456"
```

- [ ] **Step 3: 运行适配器测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/integrations/test_gitlab_adapter.py tests/unit/integrations/test_github_adapter.py -v`
Expected: FAIL with missing adapter classes

- [ ] **Step 4: 定义统一标准化事件模型**

```python
@dataclass(slots=True)
class NormalizedWebhookEvent:
    platform_type: str
    event_type: str
    action: str | None
    author: str
    title: str | None
    branch: str | None
    source_branch: str | None
    target_branch: str | None
    repo_url: str | None
    repo_full_name: str | None
    external_project_id: str | None
    external_event_id: str | None
    last_commit_id: str | None
    webhook_data: dict[str, Any]
```

- [ ] **Step 5: 用 `codereview` 逻辑实现 GitLab adapter**

```python
class GitLabAdapter(BasePlatformAdapter):
    platform_type = "gitlab"

    def parse_webhook(self, payload: dict[str, Any], headers: Mapping[str, str]) -> NormalizedWebhookEvent:
        object_attributes = payload.get("object_attributes", {})
        project = payload.get("project", {})
        return NormalizedWebhookEvent(
            platform_type="gitlab",
            event_type=payload["object_kind"],
            action=object_attributes.get("action"),
            author=payload.get("user", {}).get("username") or payload.get("user_username") or "unknown",
            title=object_attributes.get("title"),
            branch=payload.get("ref", "").replace("refs/heads/", "") or None,
            source_branch=object_attributes.get("source_branch"),
            target_branch=object_attributes.get("target_branch"),
            repo_url=project.get("web_url"),
            repo_full_name=project.get("path_with_namespace"),
            external_project_id=str(project.get("id")) if project.get("id") is not None else None,
            external_event_id=str(object_attributes.get("id") or payload.get("checkout_sha") or ""),
            last_commit_id=(object_attributes.get("last_commit") or {}).get("id") or payload.get("checkout_sha"),
            webhook_data=payload,
        )
```

- [ ] **Step 6: 用 `codereview` 逻辑实现 GitHub adapter**

```python
class GitHubAdapter(BasePlatformAdapter):
    platform_type = "github"

    def parse_webhook(self, payload: dict[str, Any], headers: Mapping[str, str]) -> NormalizedWebhookEvent:
        event_name = headers.get("X-GitHub-Event", "")
        repository = payload.get("repository", {})
        pull_request = payload.get("pull_request", {})
        return NormalizedWebhookEvent(
            platform_type="github",
            event_type="pull_request" if event_name == "pull_request" else "push",
            action=payload.get("action"),
            author=(pull_request.get("user") or payload.get("sender") or {}).get("login", "unknown"),
            title=pull_request.get("title"),
            branch=payload.get("ref", "").replace("refs/heads/", "") or None,
            source_branch=(pull_request.get("head") or {}).get("ref"),
            target_branch=(pull_request.get("base") or {}).get("ref"),
            repo_url=repository.get("html_url"),
            repo_full_name=repository.get("full_name"),
            external_project_id=str(repository.get("id")) if repository.get("id") is not None else None,
            external_event_id=headers.get("X-GitHub-Delivery"),
            last_commit_id=(pull_request.get("head") or {}).get("sha") or payload.get("after"),
            webhook_data=payload,
        )
```

- [ ] **Step 7: 运行适配器测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/integrations/test_gitlab_adapter.py tests/unit/integrations/test_github_adapter.py -v`
Expected: PASS with normalized event assertions green

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/integrations/base.py \
  backend/app/integrations/gitlab.py \
  backend/app/integrations/github.py \
  backend/app/integrations/__init__.py \
  backend/tests/unit/integrations/test_gitlab_adapter.py \
  backend/tests/unit/integrations/test_github_adapter.py
git commit -m "feat: add gitlab and github webhook adapters"
```

## Task 6: 实现 webhook API 接入与 queued 落库

**Files:**
- Create: `backend/app/api/routes/integration_webhooks.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/services/review_ingest_service.py`
- Test: `backend/tests/integration/test_integration_webhooks_api.py`

- [ ] **Step 1: 先写 GitLab webhook 接收测试**

```python
def test_gitlab_webhook_creates_queued_review_record(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    response = client.post(
        "/api/v1/integrations/webhooks/gitlab",
        json={
            "object_kind": "merge_request",
            "project": {
                "id": 100,
                "web_url": "https://gitlab.example.com/group/repo",
                "path_with_namespace": "group/repo",
            },
            "user": {"username": "alice"},
            "object_attributes": {
                "id": 500,
                "action": "open",
                "source_branch": "feature/x",
                "target_branch": "main",
                "title": "feat: x",
                "last_commit": {"id": "abc123"},
            },
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
```

- [ ] **Step 2: 写重复 webhook 去重测试**

```python
def test_gitlab_webhook_deduplicates_existing_processing_record(
    client,
    db_session,
    seeded_gitlab_project,
    fake_review_queue_service,
) -> None:
    existing = ReviewRecord(
        project_id=seeded_gitlab_project.id,
        event_type="merge_request",
        platform_type="gitlab",
        external_event_id="500",
        project_name_snapshot=seeded_gitlab_project.name,
        author="alice",
        title="feat: x",
        source_branch="feature/x",
        target_branch="main",
        review_status="processing",
        delivery_status="pending",
        last_commit_id="abc123",
        webhook_data={},
    )
    db_session.add(existing)
    db_session.commit()

    payload = {
        "object_kind": "merge_request",
        "project": {
            "id": 100,
            "web_url": "https://gitlab.example.com/group/repo",
            "path_with_namespace": "group/repo",
        },
        "user": {"username": "alice"},
        "object_attributes": {
            "id": 500,
            "action": "update",
            "source_branch": "feature/x",
            "target_branch": "main",
            "title": "feat: x",
            "last_commit": {"id": "abc123"},
        },
    }

    response = client.post("/api/v1/integrations/webhooks/gitlab", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "duplicate"
```

- [ ] **Step 3: 运行集成测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_integration_webhooks_api.py -v`
Expected: FAIL with missing route `/api/v1/integrations/webhooks/gitlab`

- [ ] **Step 4: 在 review ingest service 中新增真实 webhook 入库方法**

```python
async def ingest_webhook_event(
    self,
    *,
    project: Project,
    event: NormalizedWebhookEvent,
) -> ReviewRecord:
    existing = self._find_existing_webhook_record(project.id, event)
    if existing is not None:
        return existing

    record = ReviewRecord(
        project_id=project.id,
        event_type=event.event_type,
        platform_type=event.platform_type,
        external_event_id=event.external_event_id,
        project_name_snapshot=project.name,
        template_id_snapshot=project.template.id if project.template else None,
        template_name_snapshot=project.template.name if project.template else None,
        review_prompt_snapshot=project.template.review_prompt_template if project.template else None,
        author=event.author,
        title=event.title,
        branch=event.branch,
        source_branch=event.source_branch,
        target_branch=event.target_branch,
        review_status="queued",
        delivery_status="pending",
        url=event.repo_url,
        last_commit_id=event.last_commit_id,
        external_project_id=event.external_project_id,
        webhook_data=event.webhook_data,
    )
```

- [ ] **Step 5: 实现 webhook 路由**

```python
@router.post("/gitlab", response_model=WebhookAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def receive_gitlab_webhook(
    request: Request,
    service: IntegrationWebhookService = Depends(),
) -> WebhookAcceptedResponse:
    payload = await request.json()
    return await service.accept_gitlab(payload=payload, headers=request.headers)
```

- [ ] **Step 6: 注册 webhook 路由**

```python
from app.api.routes.integration_webhooks import router as integration_webhooks_router

api_router.include_router(integration_webhooks_router)
```

- [ ] **Step 7: 运行集成测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_integration_webhooks_api.py -v`
Expected: PASS with queued and duplicate flows green

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/api/routes/integration_webhooks.py \
  backend/app/api/router.py \
  backend/app/services/review_ingest_service.py \
  backend/tests/integration/test_integration_webhooks_api.py
git commit -m "feat: add webhook ingestion api"
```

## Task 7: 实现 worker 主执行服务

**Files:**
- Create: `backend/app/services/review_execution_service.py`
- Test: `backend/tests/unit/services/test_review_execution_service.py`

- [ ] **Step 1: 先写 queued -> reviewed 状态流转测试**

```python
def test_execution_service_marks_reviewed_after_success(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "reviewed"
    assert record.delivery_status == "delivered"
    assert record.score == 95
```

- [ ] **Step 2: 写 skipped 状态测试**

```python
def test_execution_service_marks_skipped_when_no_supported_files(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    fake_adapter_registry.register_changes(record.id, [])
    fake_adapter_registry.register_commits(
        record.id,
        [{"id": "abc123", "message": "docs: update readme", "author": "alice"}],
    )

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "skipped"
    assert record.review_result == "关注的文件没有修改"
```

- [ ] **Step 3: 写 failed 与 retry_count 测试**

```python
def test_execution_service_marks_failed_after_exception(
    db_session,
    fake_adapter_registry,
    fake_comment_service,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    fake_adapter_registry.register_changes(
        record.id,
        [{"new_path": "app.py", "diff": "+print('boom')", "additions": 1, "deletions": 0}],
    )
    fake_adapter_registry.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: trigger error", "author": "alice"}],
    )

    reviewer = ExplodingReviewer(error_message="boom")
    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=reviewer,
        comment_service=fake_comment_service,
        notification_service=fake_notification_service,
    )

    with pytest.raises(RuntimeError, match="boom"):
        service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "failed"
    assert record.retry_count == 1
    assert "boom" in record.error_message
```

- [ ] **Step 4: 运行单测确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_execution_service.py -v`
Expected: FAIL with missing `ReviewExecutionService`

- [ ] **Step 5: 实现 worker 编排服务**

```python
class ReviewExecutionService:
    def execute(self, *, review_record_id: int, attempt: int) -> None:
        record = self._get_record_or_raise(review_record_id)
        record.review_status = "processing"
        self.session.commit()

        adapter = self.adapter_registry.get(record.platform_type or "")
        changes = adapter.fetch_changes(record)
        commits = adapter.fetch_commits(record)
        filtered_changes = self._filter_changes(record, changes)
        if not filtered_changes:
            record.review_status = "skipped"
            record.review_result = "关注的文件没有修改"
            self.session.commit()
            return

        review_text = self.reviewer.review(record=record, changes=filtered_changes, commits=commits)
        record.score = self.reviewer.parse_score(review_text)
        record.review_result = review_text
        record.review_status = "reviewed"
```

- [ ] **Step 6: 把 commit 明细写入 `review_commits`**

```python
for index, commit_payload in enumerate(commits):
    self.session.add(
        ReviewCommit(
            review_record_id=record.id,
            commit_id=commit_payload["id"],
            short_commit_id=commit_payload["id"][:8],
            author=commit_payload.get("author"),
            message=commit_payload.get("message"),
            timestamp=self._to_datetime(commit_payload.get("timestamp")),
            sequence=index,
            payload=commit_payload,
        )
    )
```

- [ ] **Step 7: 记录 `agent_trace`、错误和重试计数**

```python
except Exception as exc:
    record.retry_count += 1
    record.review_status = "failed"
    record.failed_at = datetime.now(UTC)
    record.error_message = str(exc)
    record.agent_trace = {
        **record.agent_trace,
        "last_error": str(exc),
        "attempt": attempt,
    }
    self.session.commit()
    raise
```

- [ ] **Step 8: 运行单测确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_execution_service.py -v`
Expected: PASS with reviewed/skipped/failed flows green

- [ ] **Step 9: 提交这一组变更**

```bash
git add backend/app/services/review_execution_service.py \
  backend/tests/unit/services/test_review_execution_service.py
git commit -m "feat: add review execution service"
```

## Task 8: 接入评论回写与通知服务

**Files:**
- Create: `backend/app/services/review_comment_service.py`
- Create: `backend/app/services/review_notification_service.py`
- Test: `backend/tests/unit/services/test_review_execution_service.py`

- [ ] **Step 1: 先写评论失败但审查成功的测试**

```python
def test_execution_service_marks_partial_failure_when_comment_fails(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_notification_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    fake_adapter_registry.register_changes(
        record.id,
        [{"new_path": "app.py", "diff": "+print('ok')", "additions": 1, "deletions": 0}],
    )
    fake_adapter_registry.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: ok", "author": "alice"}],
    )
    comment_service = ExplodingCommentService(error_message="comment failed")

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=comment_service,
        notification_service=fake_notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.review_status == "reviewed"
    assert record.delivery_status == "comment_failed"
```

- [ ] **Step 2: 写通知失败测试**

```python
def test_execution_service_marks_partial_failure_when_notification_fails(
    db_session,
    fake_adapter_registry,
    fake_reviewer,
    fake_comment_service,
) -> None:
    record = _create_queued_review_record(db_session, platform_type="gitlab")
    fake_adapter_registry.register_changes(
        record.id,
        [{"new_path": "app.py", "diff": "+print('ok')", "additions": 1, "deletions": 0}],
    )
    fake_adapter_registry.register_commits(
        record.id,
        [{"id": "abc123", "message": "feat: ok", "author": "alice"}],
    )
    notification_service = ExplodingNotificationService(error_message="notify failed")

    service = ReviewExecutionService(
        session=db_session,
        adapter_registry=fake_adapter_registry,
        reviewer=fake_reviewer,
        comment_service=fake_comment_service,
        notification_service=notification_service,
    )

    service.execute(review_record_id=record.id, attempt=1)

    db_session.refresh(record)
    assert record.delivery_status == "notify_failed"
```

- [ ] **Step 3: 运行相关测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_execution_service.py -k partial_failure -v`
Expected: FAIL with missing delivery behavior

- [ ] **Step 4: 实现评论回写服务**

```python
class ReviewCommentService:
    def deliver(self, *, adapter: BasePlatformAdapter, record: ReviewRecord, review_result: str) -> None:
        adapter.post_review_comment(record=record, review_result=review_result)
```

- [ ] **Step 5: 实现通知服务，优先项目 bot，兜底环境变量**

```python
class ReviewNotificationService:
    def deliver(self, *, record: ReviewRecord) -> None:
        if record.project.default_bot is not None:
            self._send_via_bot(record.project.default_bot, record)
            return
        notifier.send_notification(
            content=self._build_markdown(record),
            msg_type="markdown",
            title="Code Review Result",
            project_name=record.project_name_snapshot,
            url_slug=record.url_slug,
            webhook_data=record.webhook_data,
        )
```

- [ ] **Step 6: 在执行服务中聚合投递状态**

```python
delivery_errors: list[str] = []
try:
    self.comment_service.deliver(adapter=adapter, record=record, review_result=review_text)
except Exception as exc:
    delivery_errors.append(f"comment:{exc}")

try:
    self.notification_service.deliver(record=record)
except Exception as exc:
    delivery_errors.append(f"notify:{exc}")

record.delivery_status = self._resolve_delivery_status(delivery_errors)
```

- [ ] **Step 7: 运行相关测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/services/test_review_execution_service.py -v`
Expected: PASS with `delivery_status` assertions green

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/app/services/review_comment_service.py \
  backend/app/services/review_notification_service.py \
  backend/app/services/review_execution_service.py \
  backend/tests/unit/services/test_review_execution_service.py
git commit -m "feat: add review comment and notification delivery"
```

## Task 9: 增加独立 worker 入口与端到端流程测试

**Files:**
- Create: `backend/app/workers/review_worker.py`
- Test: `backend/tests/integration/test_review_worker_flow.py`

- [ ] **Step 1: 先写 worker 消费队列的端到端测试**

```python
def test_review_worker_processes_queued_record_to_reviewed(
    db_session,
    fake_review_queue_service,
    seeded_queued_record,
    monkeypatch,
) -> None:
    fake_review_queue_service.enqueue(
        review_record_id=seeded_queued_record.id,
        platform_type="gitlab",
        attempt=1,
    )

    run_single_review_job(fake_review_queue_service, db_session)

    db_session.refresh(seeded_queued_record)
    assert seeded_queued_record.review_status == "reviewed"
```

- [ ] **Step 2: 运行端到端测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_review_worker_flow.py -v`
Expected: FAIL with missing worker entrypoint

- [ ] **Step 3: 实现单次消费函数，方便测试与生产复用**

```python
def run_single_review_job(queue_service: ReviewQueueService, session: Session) -> bool:
    message = queue_service.dequeue()
    if message is None:
        return False
    service = build_review_execution_service(session=session)
    service.execute(
        review_record_id=message.review_record_id,
        attempt=message.attempt,
    )
    return True
```

- [ ] **Step 4: 实现长轮询 worker 主循环**

```python
def main() -> None:
    queue_service = build_review_queue_service()
    while True:
        session = SessionLocal()
        try:
            processed = run_single_review_job(queue_service, session)
        finally:
            session.close()
        if not processed:
            time.sleep(1.0)
```

- [ ] **Step 5: 运行端到端测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_review_worker_flow.py -v`
Expected: PASS with queued -> reviewed flow green

- [ ] **Step 6: 提交这一组变更**

```bash
git add backend/app/workers/review_worker.py \
  backend/tests/integration/test_review_worker_flow.py
git commit -m "feat: add review worker entrypoint"
```

## Task 10: 迁入日报服务

**Files:**
- Create: `backend/app/services/daily_report_service.py`
- Create: `backend/app/workers/report_worker.py`
- Test: `backend/tests/integration/test_daily_report_service.py`

- [ ] **Step 1: 先写日报按作者去重聚合测试**

```python
def test_daily_report_service_deduplicates_by_author_and_commit_messages(db_session) -> None:
    _seed_review_record(db_session, author="alice", commit_messages=["feat: a"], review_status="reviewed")
    _seed_review_record(db_session, author="alice", commit_messages=["feat: a"], review_status="reviewed")

    service = DailyReportService(session=db_session)
    rows = service.collect_today_rows()
    assert len(rows) == 1
```

- [ ] **Step 2: 写报告发送测试**

```python
def test_daily_report_service_sends_markdown_via_notifier(monkeypatch, db_session) -> None:
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.daily_report_service.notifier.send_notification",
        lambda **kwargs: sent.update(kwargs),
    )
    _seed_review_record(
        db_session,
        author="alice",
        commit_messages=["feat: daily report"],
        review_status="reviewed",
        review_result="looks good",
    )
    service = DailyReportService(session=db_session)
    service.send_today_report()
    assert sent["msg_type"] == "markdown"
    assert sent["title"] == "代码提交日报"
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_daily_report_service.py -v`
Expected: FAIL with missing `DailyReportService`

- [ ] **Step 4: 实现日报服务**

```python
class DailyReportService:
    def collect_today_rows(self) -> list[dict[str, Any]]:
        start_at, end_at = self._today_window()
        rows = self.session.scalars(
            select(ReviewRecord)
            .where(
                ReviewRecord.review_status == "reviewed",
                ReviewRecord.updated_at >= start_at,
                ReviewRecord.updated_at <= end_at,
            )
            .order_by(ReviewRecord.author.asc(), ReviewRecord.updated_at.desc())
        ).all()
        dedup: dict[tuple[str, tuple[str, ...]], ReviewRecord] = {}
        for row in rows:
            dedup[(row.author, tuple(row.commit_messages))] = row
        return [self._to_row_payload(record) for record in dedup.values()]
```

- [ ] **Step 5: 实现定时 worker 入口**

```python
def main() -> None:
    while True:
        if cron_matches_now(settings.report_crontab_expression):
            session = SessionLocal()
            try:
                DailyReportService(session=session).send_today_report()
            finally:
                session.close()
        time.sleep(30)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_daily_report_service.py -v`
Expected: PASS with dedupe and send tests green

- [ ] **Step 7: 提交这一组变更**

```bash
git add backend/app/services/daily_report_service.py \
  backend/app/workers/report_worker.py \
  backend/tests/integration/test_daily_report_service.py
git commit -m "feat: add daily report service"
```

## Task 11: 扩展历史导入脚本与后台统计

**Files:**
- Modify: `backend/scripts/import_review_logs.py`
- Modify: `backend/app/services/member_analytics_service.py`
- Modify: `backend/app/services/dashboard_service.py`
- Test: `backend/tests/unit/scripts/test_import_review_logs.py`
- Test: `backend/tests/integration/test_member_analytics_api.py`
- Test: `backend/tests/integration/test_dashboard_api.py`

- [ ] **Step 1: 先写历史导入新字段映射测试**

```python
def test_build_mock_ingest_request_maps_platform_and_review_status() -> None:
    payload = build_mock_ingest_request(
        event_type="merge_request",
        project_key="demo",
        source_record={
            "id": 1,
            "project_name": "demo",
            "author": "alice",
            "platform": "gitlab",
            "commit_messages": "feat: a",
            "review_result": "ok",
        },
    )
    assert payload["payload"]["review_status"] == "reviewed"
    assert payload["payload"]["platform"] == "gitlab"
```

- [ ] **Step 2: 写成员分析排除失败记录测试**

```python
def test_member_analytics_excludes_failed_records_from_average_score(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project_with_member(db_session, member_name="alice")
    _create_review_record(
        db_session,
        project_id=project.id,
        author="alice",
        review_status="reviewed",
        score=90,
    )
    _create_review_record(
        db_session,
        project_id=project.id,
        author="alice",
        review_status="failed",
        score=20,
    )
    response = authenticated_superuser_client.get(
        "/api/v1/member-analytics",
        params={"page": 1, "page_size": 20, "project_id": project.id},
    )
    assert response.json()["items"][0]["review_count"] == 1
```

- [ ] **Step 3: 运行相关测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_import_review_logs.py tests/integration/test_member_analytics_api.py tests/integration/test_dashboard_api.py -v`
Expected: FAIL with missing new-field mapping or stale aggregation assumptions

- [ ] **Step 4: 扩展历史导入脚本映射**

```python
payload.update(
    {
        "platform_type": source_record.get("platform") or "gitlab",
        "delivery_status": "delivered",
        "review_status": "reviewed",
    }
)
```

- [ ] **Step 5: 调整成员分析口径**

```python
reviews = self.session.scalars(
    select(ReviewRecord)
    .where(
        ReviewRecord.project_id == project_member.project_id,
        ReviewRecord.author == project_member.member_name,
        ReviewRecord.review_status == "reviewed",
    )
    .order_by(ReviewRecord.updated_at.desc(), ReviewRecord.id.desc())
).all()
```

- [ ] **Step 6: 调整仪表盘总量与平均分口径**

```python
reviewed_average = self.session.scalar(
    select(func.avg(ReviewRecord.score)).where(ReviewRecord.review_status == "reviewed")
)
```

- [ ] **Step 7: 运行相关测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/scripts/test_import_review_logs.py tests/integration/test_member_analytics_api.py tests/integration/test_dashboard_api.py -v`
Expected: PASS with updated import and aggregation behavior

- [ ] **Step 8: 提交这一组变更**

```bash
git add backend/scripts/import_review_logs.py \
  backend/app/services/member_analytics_service.py \
  backend/app/services/dashboard_service.py \
  backend/tests/unit/scripts/test_import_review_logs.py \
  backend/tests/integration/test_member_analytics_api.py \
  backend/tests/integration/test_dashboard_api.py
git commit -m "feat: align analytics and historical import with real review flow"
```

## Task 12: 文档与运行说明收尾

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: 为 README 写失败检查清单，确认缺少 webhook / worker 说明**

```markdown
- Missing: webhook endpoints for GitLab and GitHub
- Missing: review worker startup command
- Missing: report worker startup command
- Missing: environment variables for queue and codereview compatibility
```

- [ ] **Step 2: 补充运行命令**

```markdown
```bash
uvicorn app.main:app --reload
python -m app.workers.review_worker
python -m app.workers.report_worker
```
```

- [ ] **Step 3: 补充 webhook 与环境变量配置说明**

```markdown
### Webhook Endpoints

- GitLab: `POST /api/v1/integrations/webhooks/gitlab`
- GitHub: `POST /api/v1/integrations/webhooks/github`

### Required Environment Variables

- `AI_CODE_REVIEWER_REVIEW_QUEUE_NAME`
- `AI_CODE_REVIEWER_REPORT_CRONTAB_EXPRESSION`
- `GITLAB_ACCESS_TOKEN`
- `GITHUB_ACCESS_TOKEN`
- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` 等模型密钥
```

- [ ] **Step 4: 运行 README smoke test**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/unit/test_readme_smoke.py -v`
Expected: PASS with updated commands and env documentation

- [ ] **Step 5: 提交这一组变更**

```bash
git add backend/README.md
git commit -m "docs: describe webhook workers and codereview integration"
```

## Self-Review Checklist

- `spec` 覆盖检查：
  - webhook 接入：Task 3, Task 5, Task 6
  - PostgreSQL 表结构扩展：Task 1, Task 2
  - Redis 队列与 worker：Task 4, Task 7, Task 9
  - LLM 审查编排：Task 7
  - 评论回写与通知：Task 8
  - 日报迁移：Task 10
  - 历史数据导入：Task 11
  - 管理台与统计兼容：Task 2, Task 11
- placeholder 扫描：
  - 无占位式 `TODO`、`TBD`、`implement later`、`similar to task`、`...`
- 类型一致性检查：
  - 平台枚举统一使用 `gitlab | github`
  - 任务状态统一使用 `queued | processing | reviewed | skipped | failed`
  - 投递状态统一使用 `pending | delivered | comment_failed | notify_failed | partial_failed`
