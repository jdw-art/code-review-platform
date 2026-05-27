# Phase 2A Backend Admin Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为第二阶段管理后台落地后端管理域，包含项目、项目模板、模型、机器人、审查记录、成员分析、仪表盘与审计日志能力。

**Architecture:** 沿用现有 FastAPI + SQLAlchemy + Service 分层，不新增 repository 层。新增领域模型、Pydantic schema、service、route 与 Alembic 迁移，接口按后台页面能力直接映射；敏感字段统一采用可逆加密存储、接口脱敏返回、审计日志脱敏落库。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy 2.x、Alembic、PostgreSQL、Redis、pytest、cryptography

---

## File Map

### Existing files to modify

- `backend/pyproject.toml`：补充加密依赖。
- `backend/app/core/config.py`：增加第二阶段配置项，例如敏感字段加密密钥。
- `backend/app/api/router.py`：注册新增业务路由。
- `backend/app/db/models/__init__.py`：导出新增 ORM 模型。
- `backend/app/services/bootstrap.py`：挂接第二阶段权限、菜单、系统模板等初始化逻辑。
- `backend/tests/integration/test_openapi_docs.py`：扩充新增业务接口的中文文档断言。
- `backend/tests/unit/db/test_models_schema.py`：保留原有一阶段表断言，并为新表断言腾出扩展入口。

### New backend core files

- `backend/app/core/crypto.py`
- `backend/app/services/admin_console_bootstrap.py`

### New ORM model files

- `backend/app/db/models/project.py`
- `backend/app/db/models/project_template.py`
- `backend/app/db/models/llm_model.py`
- `backend/app/db/models/notification_bot.py`
- `backend/app/db/models/review_record.py`
- `backend/app/db/models/review_commit.py`
- `backend/app/db/models/project_member.py`
- `backend/app/db/models/audit_log.py`

### New schema files

- `backend/app/schemas/pagination.py`
- `backend/app/schemas/project.py`
- `backend/app/schemas/project_template.py`
- `backend/app/schemas/llm_model.py`
- `backend/app/schemas/notification_bot.py`
- `backend/app/schemas/review_record.py`
- `backend/app/schemas/dashboard.py`
- `backend/app/schemas/member_analytics.py`
- `backend/app/schemas/audit_log.py`

### New service files

- `backend/app/services/project_service.py`
- `backend/app/services/project_template_service.py`
- `backend/app/services/llm_model_service.py`
- `backend/app/services/notification_bot_service.py`
- `backend/app/services/review_ingest_service.py`
- `backend/app/services/review_record_service.py`
- `backend/app/services/dashboard_service.py`
- `backend/app/services/member_analytics_service.py`
- `backend/app/services/audit_log_service.py`

### New route files

- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/project_templates.py`
- `backend/app/api/routes/llm_models.py`
- `backend/app/api/routes/notification_bots.py`
- `backend/app/api/routes/review_records.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/member_analytics.py`
- `backend/app/api/routes/audit_logs.py`

### New migration and test files

- `backend/alembic/versions/0002_create_phase2_admin_console_schema.py`
- `backend/tests/unit/core/test_crypto.py`
- `backend/tests/unit/db/test_phase2_models_schema.py`
- `backend/tests/unit/services/test_project_service.py`
- `backend/tests/unit/services/test_review_ingest_service.py`
- `backend/tests/unit/services/test_audit_log_service.py`
- `backend/tests/integration/test_projects_api.py`
- `backend/tests/integration/test_project_templates_api.py`
- `backend/tests/integration/test_llm_models_api.py`
- `backend/tests/integration/test_notification_bots_api.py`
- `backend/tests/integration/test_review_records_api.py`
- `backend/tests/integration/test_dashboard_api.py`
- `backend/tests/integration/test_member_analytics_api.py`
- `backend/tests/integration/test_audit_logs_api.py`

### Files intentionally not touched in Phase 2A

- `backend/app/security/tokens.py`：现有 JWT 逻辑够用。
- `backend/app/security/passwords.py`：密码哈希逻辑沿用 Phase 1。
- `backend/app/api/routes/auth.py` 的认证主流程只补审计埋点，不改协议。

### Task 1: Add Secret Encryption Infrastructure

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/core/crypto.py`
- Test: `backend/tests/unit/core/test_crypto.py`
- Test: `backend/tests/unit/test_config_smoke.py`

- [ ] **Step 1: Write the failing tests**

```python
from cryptography.fernet import Fernet

from app.core.crypto import SecretCipher
from app.core.config import Settings


def test_secret_cipher_round_trip() -> None:
    cipher = SecretCipher(Fernet.generate_key().decode("utf-8"))
    encrypted = cipher.encrypt_text("top-secret")

    assert encrypted != "top-secret"
    assert cipher.decrypt_text(encrypted) == "top-secret"


def test_settings_expose_secret_encryption_key() -> None:
    settings = Settings()
    assert settings.secret_encryption_key
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/core/test_crypto.py tests/unit/test_config_smoke.py -v`

Expected: FAIL with import error for `app.core.crypto` or missing `secret_encryption_key`.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    secret_encryption_key: str = "change-me-fernet-key"


# backend/app/core/crypto.py
from cryptography.fernet import Fernet


class SecretCipher:
    """负责对 API Key、Webhook Secret 等可逆敏感字段做加解密。"""

    def __init__(self, raw_key: str) -> None:
        self.fernet = Fernet(raw_key.encode("utf-8"))

    def encrypt_text(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_text(self, value: str) -> str:
        return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
```

Also add:

```toml
# backend/pyproject.toml
"cryptography>=43.0.0",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/core/test_crypto.py tests/unit/test_config_smoke.py -v`

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/core/config.py backend/app/core/crypto.py backend/tests/unit/core/test_crypto.py backend/tests/unit/test_config_smoke.py
git commit -m "feat(backend): add secret encryption infrastructure"
```

### Task 2: Create Phase 2 ORM Models and Migration

**Files:**
- Create: `backend/app/db/models/project.py`
- Create: `backend/app/db/models/project_template.py`
- Create: `backend/app/db/models/llm_model.py`
- Create: `backend/app/db/models/notification_bot.py`
- Create: `backend/app/db/models/review_record.py`
- Create: `backend/app/db/models/review_commit.py`
- Create: `backend/app/db/models/project_member.py`
- Create: `backend/app/db/models/audit_log.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/alembic/versions/0002_create_phase2_admin_console_schema.py`
- Test: `backend/tests/unit/db/test_phase2_models_schema.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from sqlalchemy import inspect


def test_phase2_admin_console_tables_exist(db_session) -> None:
    inspector = inspect(db_session.bind)
    table_names = set(inspector.get_table_names())

    assert "projects" in table_names
    assert "project_templates" in table_names
    assert "llm_models" in table_names
    assert "notification_bots" in table_names
    assert "review_records" in table_names
    assert "review_commits" in table_names
    assert "project_members" in table_names
    assert "audit_logs" in table_names


def test_review_records_keep_template_snapshots(db_session) -> None:
    inspector = inspect(db_session.bind)
    columns = {column["name"] for column in inspector.get_columns("review_records")}

    assert "template_id_snapshot" in columns
    assert "template_name_snapshot" in columns
    assert "review_prompt_snapshot" in columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/db/test_phase2_models_schema.py -v`

Expected: FAIL because the new tables and columns do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/db/models/project.py
from sqlalchemy import BigInteger, Boolean, ForeignKey, JSON, String, Text, true, false
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Project(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    platform_type: Mapped[str] = mapped_column(String(50), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    review_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    template_id: Mapped[int | None] = mapped_column(ForeignKey("project_templates.id"))
    default_model_id: Mapped[int | None] = mapped_column(ForeignKey("llm_models.id"))
    default_bot_id: Mapped[int | None] = mapped_column(ForeignKey("notification_bots.id"))
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
```

```python
# backend/app/db/models/review_record.py
class ReviewRecord(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_records"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    template_id_snapshot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    template_name_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    webhook_data: Mapped[dict] = mapped_column(JSON, default=dict)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
```

Create the Alembic migration with explicit table definitions such as:

```python
def upgrade() -> None:
    op.create_table(
        "project_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("file_extensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("review_prompt_template", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
```

Then add the remaining tables plus indexes on:

- `projects.key`
- `project_templates.code`
- `review_records(project_id, event_type, created_at)`
- `review_records(external_event_id)`
- `audit_logs(created_at)`

Update model exports:

```python
# backend/app/db/models/__init__.py
from app.db.models.audit_log import AuditLog
from app.db.models.llm_model import LlmModel
from app.db.models.notification_bot import NotificationBot
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.project_template import ProjectTemplate
from app.db.models.review_commit import ReviewCommit
from app.db.models.review_record import ReviewRecord
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/db/test_phase2_models_schema.py -v`

Expected: PASS and the migration-generated schema matches the ORM definitions.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models backend/alembic/versions/0002_create_phase2_admin_console_schema.py backend/tests/unit/db/test_phase2_models_schema.py
git commit -m "feat(backend): add phase 2 admin console schema"
```

### Task 3: Implement Projects and Project Template APIs

**Files:**
- Create: `backend/app/schemas/pagination.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/schemas/project_template.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/services/project_template_service.py`
- Create: `backend/app/services/admin_console_bootstrap.py`
- Create: `backend/app/api/routes/projects.py`
- Create: `backend/app/api/routes/project_templates.py`
- Modify: `backend/app/services/bootstrap.py`
- Test: `backend/tests/unit/services/test_project_service.py`
- Test: `backend/tests/integration/test_projects_api.py`
- Test: `backend/tests/integration/test_project_templates_api.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_project_rejects_inactive_template(db_session):
    service = ProjectService(session=db_session)
    payload = ProjectCreateRequest(
        name="demo",
        key="demo",
        platform_type="gitlab",
        default_branch="main",
        template_id=2,
    )

    with pytest.raises(DomainConflictError):
        anyio.run(service.create_project, payload)


def test_project_templates_api_exposes_chinese_openapi(client, authenticated_superuser_client):
    response = client.get("/openapi.json")
    operation = response.json()["paths"]["/api/v1/project-templates"]["get"]

    assert operation["summary"] == "获取项目模板列表"
    assert "分页返回项目模板列表" in operation["description"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/services/test_project_service.py tests/integration/test_projects_api.py tests/integration/test_project_templates_api.py -v`

Expected: FAIL because the services, schemas, bootstrap seeds, and routes do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/schemas/project_template.py
class ProjectTemplateCreateRequest(BaseModel):
    name: str
    code: str
    description: str | None = None
    file_extensions: list[str]
    review_prompt_template: str | None = None
    is_active: bool = True


class ProjectTemplateResponse(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    file_extensions: list[str]
    review_prompt_template: str | None
    review_prompt_configured: bool
    is_system: bool
    is_active: bool
```

```python
# backend/app/services/project_service.py
class ProjectService:
    """负责项目列表、创建、更新、启停与表单选项逻辑。"""

    async def create_project(self, payload: ProjectCreateRequest) -> ProjectResponse:
        template = self._get_active_template_or_none(payload.template_id)
        if payload.template_id and template is None:
            raise DomainConflictError(
                code="PROJECT_TEMPLATE_INACTIVE",
                message="项目模板未启用，不能绑定到项目。",
            )
```

```python
# backend/app/api/routes/project_templates.py
@router.get(
    "",
    response_model=PageResponse[ProjectTemplateResponse],
    dependencies=[Depends(require_permission("project_template:read"))],
    summary="获取项目模板列表",
    description="分页返回项目模板列表、支持的文件扩展名和 Review 提示词配置状态。",
)
async def list_project_templates(
    query: PageQuery = Depends(),
    service: ProjectTemplateService = Depends(),
) -> PageResponse[ProjectTemplateResponse]:
    return await service.list_templates(query)
```

Bootstrap seeds should include at minimum:

- permissions: `project:*`, `project_template:*`
- menus: `项目管理`, `项目模板管理`
- system templates: `java-default`, `frontend-vue-ts`, `go-default`, `fullstack-common`

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_project_service.py tests/integration/test_projects_api.py tests/integration/test_project_templates_api.py -v`

Expected: PASS for CRUD, status validation, option endpoints, and Chinese OpenAPI metadata.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/pagination.py backend/app/schemas/project.py backend/app/schemas/project_template.py backend/app/services/project_service.py backend/app/services/project_template_service.py backend/app/services/admin_console_bootstrap.py backend/app/services/bootstrap.py backend/app/api/routes/projects.py backend/app/api/routes/project_templates.py backend/tests/unit/services/test_project_service.py backend/tests/integration/test_projects_api.py backend/tests/integration/test_project_templates_api.py
git commit -m "feat(backend): add project and template management apis"
```

### Task 4: Implement Model, Bot, and Audit Log Capabilities

**Files:**
- Create: `backend/app/schemas/llm_model.py`
- Create: `backend/app/schemas/notification_bot.py`
- Create: `backend/app/schemas/audit_log.py`
- Create: `backend/app/services/llm_model_service.py`
- Create: `backend/app/services/notification_bot_service.py`
- Create: `backend/app/services/audit_log_service.py`
- Create: `backend/app/api/routes/llm_models.py`
- Create: `backend/app/api/routes/notification_bots.py`
- Create: `backend/app/api/routes/audit_logs.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/routes/users.py`
- Modify: `backend/app/api/routes/roles.py`
- Modify: `backend/app/api/routes/permissions.py`
- Modify: `backend/app/api/routes/menus.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/services/user_service.py`
- Modify: `backend/app/services/rbac_service.py`
- Test: `backend/tests/unit/services/test_audit_log_service.py`
- Test: `backend/tests/integration/test_llm_models_api.py`
- Test: `backend/tests/integration/test_notification_bots_api.py`
- Test: `backend/tests/integration/test_audit_logs_api.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_mask_sensitive_fields_before_audit_log_persistence() -> None:
    sanitized = sanitize_request_payload(
        {"password": "123456", "api_key": "sk-live", "secret": "bot-secret"}
    )

    assert sanitized["password"] == "***"
    assert sanitized["api_key"] == "***"
    assert sanitized["secret"] == "***"


def test_model_api_never_returns_plaintext_api_key(client, authenticated_superuser_client):
    response = client.post(
        "/api/v1/models",
        json={"name": "gpt-4.1", "provider": "openai", "model_code": "gpt-4.1", "api_key": "sk-live"},
    )

    body = response.json()
    assert "api_key" not in body
    assert body["api_key_masked"].startswith("sk-")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/services/test_audit_log_service.py tests/integration/test_llm_models_api.py tests/integration/test_notification_bots_api.py tests/integration/test_audit_logs_api.py -v`

Expected: FAIL because the routes, services, and sanitization helpers do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/services/audit_log_service.py
SENSITIVE_KEYS = {"password", "current_password", "new_password", "api_key", "secret", "token", "refresh_token"}


def sanitize_request_payload(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    sanitized: dict[str, object] = {}
    for key, value in payload.items():
        sanitized[key] = "***" if key in SENSITIVE_KEYS else value
    return sanitized
```

```python
# backend/app/services/llm_model_service.py
class LlmModelService:
    @staticmethod
    def _mask_secret(raw_secret: str) -> str:
        if len(raw_secret) <= 6:
            return "***"
        return f"{raw_secret[:3]}***{raw_secret[-2:]}"

    async def create_model(self, payload: LlmModelCreateRequest) -> LlmModelResponse:
        encrypted = self.cipher.encrypt_text(payload.api_key)
        model = LlmModel(
            name=payload.name,
            provider=payload.provider,
            model_code=payload.model_code,
            api_key_encrypted=encrypted,
            api_key_masked=self._mask_secret(payload.api_key),
        )
```

```python
# backend/app/api/routes/audit_logs.py
@router.get(
    "",
    response_model=PageResponse[AuditLogResponse],
    dependencies=[Depends(require_permission("audit_log:read"))],
    summary="获取系统日志列表",
    description="分页返回后台操作审计日志，敏感字段以脱敏形式展示。",
)
async def list_audit_logs(
    query: PageQuery = Depends(),
    service: AuditLogService = Depends(),
) -> PageResponse[AuditLogResponse]:
    return await service.list_logs(query)
```

When retrofitting existing routes, pass an `AuditActionContext` into services so these actions are persisted:

- login / logout / logout-all / change-password
- user CRUD / status / reset-password / assign-role
- role / permission / menu mutating operations

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_audit_log_service.py tests/integration/test_llm_models_api.py tests/integration/test_notification_bots_api.py tests/integration/test_audit_logs_api.py -v`

Expected: PASS for masked responses, sanitized audit payloads, and audit log listing/detail endpoints.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/llm_model.py backend/app/schemas/notification_bot.py backend/app/schemas/audit_log.py backend/app/services/llm_model_service.py backend/app/services/notification_bot_service.py backend/app/services/audit_log_service.py backend/app/api/routes/llm_models.py backend/app/api/routes/notification_bots.py backend/app/api/routes/audit_logs.py backend/app/api/routes/auth.py backend/app/api/routes/users.py backend/app/api/routes/roles.py backend/app/api/routes/permissions.py backend/app/api/routes/menus.py backend/app/services/auth_service.py backend/app/services/user_service.py backend/app/services/rbac_service.py backend/tests/unit/services/test_audit_log_service.py backend/tests/integration/test_llm_models_api.py backend/tests/integration/test_notification_bots_api.py backend/tests/integration/test_audit_logs_api.py
git commit -m "feat(backend): add model bot and audit log management"
```

### Task 5: Implement Review Records, Mock Ingest, Dashboard, and Member Analytics

**Files:**
- Create: `backend/app/schemas/review_record.py`
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/schemas/member_analytics.py`
- Create: `backend/app/services/review_ingest_service.py`
- Create: `backend/app/services/review_record_service.py`
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/services/member_analytics_service.py`
- Create: `backend/app/api/routes/review_records.py`
- Create: `backend/app/api/routes/dashboard.py`
- Create: `backend/app/api/routes/member_analytics.py`
- Test: `backend/tests/unit/services/test_review_ingest_service.py`
- Test: `backend/tests/integration/test_review_records_api.py`
- Test: `backend/tests/integration/test_dashboard_api.py`
- Test: `backend/tests/integration/test_member_analytics_api.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_mock_ingest_prefers_outer_project_locator(db_session):
    service = ReviewIngestService(session=db_session)
    payload = MockReviewIngestRequest(
        event_type="merge_request",
        project_key="demo-key",
        payload={
            "project_name": "stale-display-name",
            "author": "alice",
            "commits": [{"id": "abc123", "message": "feat: add api"}],
            "url_slug": "mr-1",
            "last_commit_id": "abc123",
            "review_result": "ok",
            "webhook_data": {},
            "updated_at": 1710000000,
        },
    )

    result = anyio.run(service.ingest_mock_event, payload)
    assert result.project_key == "demo-key"


def test_dashboard_overview_aggregates_review_scores(client, authenticated_superuser_client):
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    assert "average_score" in response.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/services/test_review_ingest_service.py tests/integration/test_review_records_api.py tests/integration/test_dashboard_api.py tests/integration/test_member_analytics_api.py -v`

Expected: FAIL because mock ingest, analytics, and dashboard services are missing.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/schemas/review_record.py
class MockReviewIngestRequest(BaseModel):
    event_type: Literal["push", "merge_request"]
    project_id: int | None = None
    project_key: str | None = None
    source: str = "mock"
    payload: dict[str, Any]
```

```python
# backend/app/services/review_ingest_service.py
class ReviewIngestService:
    async def ingest_mock_event(self, request: MockReviewIngestRequest) -> ReviewIngestResponse:
        project = self._resolve_project(project_id=request.project_id, project_key=request.project_key, payload=request.payload)
        template = project.template
        review_record = ReviewRecord(
            project_id=project.id,
            event_type=request.event_type,
            project_name_snapshot=project.name,
            template_id_snapshot=template.id if template else None,
            template_name_snapshot=template.name if template else None,
            review_prompt_snapshot=template.review_prompt_template if template else None,
            author=str(request.payload["author"]),
            commit_count=len(request.payload.get("commits", [])),
            commit_messages="; ".join(commit["message"].strip() for commit in request.payload.get("commits", [])),
            webhook_data=request.payload.get("webhook_data", {}),
        )
```

```python
# backend/app/services/dashboard_service.py
class DashboardService:
    async def get_overview(self) -> DashboardOverviewResponse:
        return DashboardOverviewResponse(
            total_projects=self._count_projects(),
            active_projects=self._count_active_projects(),
            total_review_records=self._count_review_records(),
            average_score=self._average_review_score(),
        )
```

```python
# backend/app/api/routes/review_records.py
@router.post(
    "/mock-ingest",
    response_model=ReviewIngestResponse,
    dependencies=[Depends(require_permission("review_record:import"))],
    summary="导入模拟审查事件",
    description="接收双层结构的 mock 审查事件请求，并写入统一的审查记录与 commit 明细。",
)
async def ingest_mock_review(
    payload: MockReviewIngestRequest,
    service: ReviewIngestService = Depends(),
) -> ReviewIngestResponse:
    return await service.ingest_mock_event(payload)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_review_ingest_service.py tests/integration/test_review_records_api.py tests/integration/test_dashboard_api.py tests/integration/test_member_analytics_api.py -v`

Expected: PASS for mock ingest, filters, review detail/raw endpoints, dashboard aggregations, and member analytics listing/detail.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/review_record.py backend/app/schemas/dashboard.py backend/app/schemas/member_analytics.py backend/app/services/review_ingest_service.py backend/app/services/review_record_service.py backend/app/services/dashboard_service.py backend/app/services/member_analytics_service.py backend/app/api/routes/review_records.py backend/app/api/routes/dashboard.py backend/app/api/routes/member_analytics.py backend/tests/unit/services/test_review_ingest_service.py backend/tests/integration/test_review_records_api.py backend/tests/integration/test_dashboard_api.py backend/tests/integration/test_member_analytics_api.py
git commit -m "feat(backend): add review records and analytics apis"
```

### Task 6: Wire Routers, OpenAPI Assertions, and Full Verification

**Files:**
- Modify: `backend/app/api/router.py`
- Modify: `backend/tests/integration/test_openapi_docs.py`
- Modify: `backend/app/services/admin_console_bootstrap.py`
- Modify: `backend/app/services/bootstrap.py`
- Test: `backend/tests/integration/test_openapi_docs.py`
- Test: `backend/tests/integration/test_security_invariants.py`

- [ ] **Step 1: Write the failing integration assertions**

```python
expected_operations |= {
    ("/api/v1/projects", "get"),
    ("/api/v1/projects", "post"),
    ("/api/v1/project-templates", "get"),
    ("/api/v1/models", "get"),
    ("/api/v1/bots", "get"),
    ("/api/v1/review-records", "get"),
    ("/api/v1/review-records/mock-ingest", "post"),
    ("/api/v1/dashboard/overview", "get"),
    ("/api/v1/member-analytics", "get"),
    ("/api/v1/audit-logs", "get"),
}
```

- [ ] **Step 2: Run verification to confirm failures surface**

Run: `cd backend && pytest tests/integration/test_openapi_docs.py tests/integration/test_security_invariants.py -v`

Expected: FAIL until routers are registered, summaries/descriptions are present, and seeded permissions/menus are discoverable.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/api/router.py
api_router.include_router(dashboard_router)
api_router.include_router(projects_router)
api_router.include_router(project_templates_router)
api_router.include_router(llm_models_router)
api_router.include_router(notification_bots_router)
api_router.include_router(review_records_router)
api_router.include_router(member_analytics_router)
api_router.include_router(audit_logs_router)
```

```python
# backend/app/services/bootstrap.py
def _bootstrap_once(session: Session, settings: Settings) -> None:
    role = _get_or_create_super_admin_role(session)
    user = _get_or_create_bootstrap_admin(session, settings)
    _ensure_bootstrap_admin_role(user, role)
    bootstrap_admin_console_metadata(session)
```

Also extend the admin console bootstrap seed list with:

- new permissions for dashboard / project / template / review_record / member_analytics / model / bot / audit_log
- new menus for dashboard, project management, template management, review records, member analytics, model management, notification robot, system logs

- [ ] **Step 4: Run the full backend verification**

Run:

```bash
cd backend
alembic upgrade head
pytest -v
```

Expected:

- `alembic upgrade head` completes without migration errors
- all backend unit and integration tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/router.py backend/tests/integration/test_openapi_docs.py backend/app/services/admin_console_bootstrap.py backend/app/services/bootstrap.py
git commit -m "feat(backend): wire phase 2 admin console backend"
```
