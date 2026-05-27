# Phase 1 Auth and RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 FastAPI backend for authentication, JWT session control, and RBAC management described in the approved spec.

**Architecture:** Create a standalone backend app under `backend/` with a modular FastAPI structure: `auth`, `users`, `rbac`, `me`, and `infra/security`. Use PostgreSQL for persistent state, Redis for refresh-session control, JWT for access and refresh tokens, and explicit permission guards for protected APIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic Settings, Authlib, Redis, PostgreSQL, Argon2id, pytest

---

## File Structure

Create and maintain this structure during implementation:

- `backend/pyproject.toml`: dependency and tooling configuration
- `backend/.env.example`: local environment template for `ai_code_reviewer`
- `backend/README.md`: backend setup and run instructions
- `backend/alembic.ini`: Alembic configuration
- `backend/alembic/env.py`: migration runtime config
- `backend/alembic/versions/0001_create_auth_rbac_schema.py`: initial schema migration
- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/api/router.py`: top-level API router
- `backend/app/api/routes/auth.py`: auth endpoints
- `backend/app/api/routes/me.py`: current-user endpoints
- `backend/app/api/routes/users.py`: user management endpoints
- `backend/app/api/routes/roles.py`: role management endpoints
- `backend/app/api/routes/permissions.py`: permission management endpoints
- `backend/app/api/routes/menus.py`: menu management endpoints
- `backend/app/core/config.py`: environment-backed settings
- `backend/app/core/logging.py`: app logging setup
- `backend/app/db/base.py`: SQLAlchemy declarative base
- `backend/app/db/session.py`: engine and session factory
- `backend/app/db/models/user.py`: user model
- `backend/app/db/models/role.py`: role model
- `backend/app/db/models/permission.py`: permission model
- `backend/app/db/models/menu.py`: menu model
- `backend/app/db/models/refresh_session.py`: refresh session model
- `backend/app/db/models/associations.py`: join tables
- `backend/app/db/models/__init__.py`: model exports
- `backend/app/schemas/common.py`: shared response models
- `backend/app/schemas/auth.py`: auth request/response schemas
- `backend/app/schemas/me.py`: current-user response schemas
- `backend/app/schemas/user.py`: user schemas
- `backend/app/schemas/role.py`: role schemas
- `backend/app/schemas/permission.py`: permission schemas
- `backend/app/schemas/menu.py`: menu schemas
- `backend/app/security/passwords.py`: Argon2id helpers
- `backend/app/security/tokens.py`: JWT issue and verify helpers
- `backend/app/security/redis_store.py`: Redis refresh-session operations
- `backend/app/security/deps.py`: auth and permission dependencies
- `backend/app/services/bootstrap.py`: startup admin and system resource bootstrap
- `backend/app/services/auth_service.py`: login, refresh, logout, change-password flows
- `backend/app/services/user_service.py`: user CRUD and role assignment
- `backend/app/services/rbac_service.py`: role, permission, menu CRUD and assignment
- `backend/app/services/access_context.py`: permission aggregation and menu tree assembly
- `backend/tests/conftest.py`: test app, DB session, Redis fixtures
- `backend/tests/unit/security/test_passwords.py`
- `backend/tests/unit/security/test_tokens.py`
- `backend/tests/unit/services/test_access_context.py`
- `backend/tests/unit/services/test_bootstrap.py`
- `backend/tests/integration/test_auth_api.py`
- `backend/tests/integration/test_me_api.py`
- `backend/tests/integration/test_users_api.py`
- `backend/tests/integration/test_roles_api.py`
- `backend/tests/integration/test_permissions_api.py`
- `backend/tests/integration/test_menus_api.py`

## Task 1: Scaffold the Backend Project

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/README.md`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`

- [ ] **Step 1: Write the failing configuration smoke test**

```python
# backend/tests/unit/test_config_smoke.py
from app.core.config import Settings


def test_settings_use_project_defaults():
    settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="ai_code_reviewer",
        postgres_user="postgres",
        postgres_password="postgres",
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
    )

    assert settings.postgres_db == "ai_code_reviewer"
    assert settings.redis_port == 6379
    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 7
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `cd backend && pytest tests/unit/test_config_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` or missing `Settings`.

- [ ] **Step 3: Create the project skeleton and settings implementation**

```toml
# backend/pyproject.toml
[project]
name = "ai-code-reviewer-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
  "psycopg[binary]>=3.2.0",
  "redis>=5.0.0",
  "authlib>=1.3.0",
  "pwdlib[argon2]>=0.2.0",
  "pydantic-settings>=2.4.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AI_CODE_REVIEWER_")

    app_name: str = "AI Code Reviewer"
    api_prefix: str = "/api/v1"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_code_reviewer"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    jwt_secret_key: str = "change-me-in-env"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "jdw112233"
```

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import Settings


settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)
```

- [ ] **Step 4: Re-run the smoke test**

Run: `cd backend && pytest tests/unit/test_config_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit the scaffold**

```bash
git add backend/pyproject.toml backend/.env.example backend/README.md backend/app backend/tests/unit/test_config_smoke.py
git commit -m "feat: scaffold backend application"
```

## Task 2: Add Database Core and Initial Schema Models

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_create_auth_rbac_schema.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/user.py`
- Create: `backend/app/db/models/role.py`
- Create: `backend/app/db/models/permission.py`
- Create: `backend/app/db/models/menu.py`
- Create: `backend/app/db/models/refresh_session.py`
- Create: `backend/app/db/models/associations.py`
- Create: `backend/tests/unit/db/test_models_schema.py`

- [ ] **Step 1: Write the failing schema test**

```python
# backend/tests/unit/db/test_models_schema.py
from app.db.models import Menu, Permission, RefreshSession, Role, User


def test_primary_keys_use_bigint():
    assert str(User.__table__.c.id.type) == "BIGINT"
    assert str(Role.__table__.c.id.type) == "BIGINT"
    assert str(Permission.__table__.c.id.type) == "BIGINT"
    assert str(Menu.__table__.c.id.type) == "BIGINT"
    assert str(RefreshSession.__table__.c.id.type) == "BIGINT"
```

- [ ] **Step 2: Run the schema test to confirm it fails**

Run: `cd backend && pytest tests/unit/db/test_models_schema.py -v`
Expected: FAIL because the models package does not exist yet.

- [ ] **Step 3: Implement the base, session, models, and initial migration**

```python
# backend/app/db/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger


class Base(DeclarativeBase):
    pass


class BigIntPrimaryKeyMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
```

```python
# backend/app/db/models/user.py
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, BigIntPrimaryKeyMixin


class User(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
```

```python
# backend/alembic/versions/0001_create_auth_rbac_schema.py
def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
```

- [ ] **Step 4: Re-run the schema test**

Run: `cd backend && pytest tests/unit/db/test_models_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit the database foundation**

```bash
git add backend/alembic.ini backend/alembic backend/app/db backend/tests/unit/db/test_models_schema.py
git commit -m "feat: add auth rbac database schema"
```

## Task 3: Implement Password Hashing, JWT Helpers, and Redis Store

**Files:**
- Create: `backend/app/security/__init__.py`
- Create: `backend/app/security/passwords.py`
- Create: `backend/app/security/tokens.py`
- Create: `backend/app/security/redis_store.py`
- Create: `backend/tests/unit/security/test_passwords.py`
- Create: `backend/tests/unit/security/test_tokens.py`

- [ ] **Step 1: Write the failing security tests**

```python
# backend/tests/unit/security/test_passwords.py
from app.security.passwords import hash_password, verify_password


def test_passwords_are_hashed_and_verified():
    password_hash = hash_password("jdw112233")

    assert password_hash != "jdw112233"
    assert verify_password("jdw112233", password_hash) is True
    assert verify_password("wrong", password_hash) is False
```

```python
# backend/tests/unit/security/test_tokens.py
from app.security.tokens import issue_access_token, issue_refresh_token


def test_tokens_include_expected_claims():
    access_token = issue_access_token(user_id=1, username="admin", is_superuser=True)
    refresh_token = issue_refresh_token(user_id=1, session_jti="jti-123")

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
```

- [ ] **Step 2: Run the security tests to verify they fail**

Run: `cd backend && pytest tests/unit/security/test_passwords.py tests/unit/security/test_tokens.py -v`
Expected: FAIL because `app.security` modules do not exist.

- [ ] **Step 3: Implement the password, token, and Redis helpers**

```python
# backend/app/security/passwords.py
from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)
```

```python
# backend/app/security/tokens.py
from datetime import UTC, datetime, timedelta
from authlib.jose import jwt
from app.core.config import Settings


settings = Settings()


def issue_access_token(*, user_id: int, username: str, is_superuser: bool) -> str:
    claims = {
        "sub": str(user_id),
        "username": username,
        "is_superuser": is_superuser,
        "token_type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret_key).decode()


def issue_refresh_token(*, user_id: int, session_jti: str) -> str:
    claims = {
        "sub": str(user_id),
        "jti": session_jti,
        "token_type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
    }
    return jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret_key).decode()


def decode_token(token: str, expected_token_type: str) -> dict:
    claims = jwt.decode(token, settings.jwt_secret_key)
    claims.validate()
    if claims["token_type"] != expected_token_type:
        raise ValueError(f"Expected {expected_token_type} token.")
    return dict(claims)
```

```python
# backend/app/security/redis_store.py
from redis.asyncio import Redis


class RefreshSessionStore:
    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def save_refresh_session(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        await self.redis.setex(f"auth:refresh:{jti}", ttl_seconds, str(user_id))
        await self.redis.sadd(f"auth:user_refresh_index:{user_id}", jti)
```

- [ ] **Step 4: Re-run the unit tests**

Run: `cd backend && pytest tests/unit/security/test_passwords.py tests/unit/security/test_tokens.py -v`
Expected: PASS

- [ ] **Step 5: Commit the security primitives**

```bash
git add backend/app/security backend/tests/unit/security
git commit -m "feat: add password token and redis helpers"
```

## Task 4: Bootstrap the Initial Admin and System Role

**Files:**
- Create: `backend/app/services/bootstrap.py`
- Create: `backend/tests/unit/services/test_bootstrap.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/db/models/role.py`
- Modify: `backend/app/db/models/associations.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
# backend/tests/unit/services/test_bootstrap.py
from app.services.bootstrap import build_bootstrap_admin_payload


def test_bootstrap_admin_requires_password_change():
    payload = build_bootstrap_admin_payload()

    assert payload["username"] == "admin"
    assert payload["is_superuser"] is True
    assert payload["must_change_password"] is True
```

- [ ] **Step 2: Run the bootstrap test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_bootstrap.py -v`
Expected: FAIL because `build_bootstrap_admin_payload` does not exist.

- [ ] **Step 3: Implement bootstrap logic and startup hook**

```python
# backend/app/services/bootstrap.py
from app.core.config import Settings
from app.security.passwords import hash_password


def build_bootstrap_admin_payload() -> dict[str, object]:
    settings = Settings()
    return {
        "username": settings.bootstrap_admin_username,
        "password_hash": hash_password(settings.bootstrap_admin_password),
        "is_active": True,
        "is_superuser": True,
        "must_change_password": True,
    }
```

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.bootstrap import run_bootstrap


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_bootstrap()
    yield
```

- [ ] **Step 4: Re-run the bootstrap test**

Run: `cd backend && pytest tests/unit/services/test_bootstrap.py -v`
Expected: PASS

- [ ] **Step 5: Commit bootstrap behavior**

```bash
git add backend/app/main.py backend/app/services/bootstrap.py backend/app/db/models/role.py backend/app/db/models/associations.py backend/tests/unit/services/test_bootstrap.py
git commit -m "feat: bootstrap initial admin and role"
```

## Task 5: Build Auth Service and Auth API

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/routes/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/integration/test_auth_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write the failing auth integration test**

```python
# backend/tests/integration/test_auth_api.py
def test_login_returns_token_pair(client, bootstrap_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["must_change_password"] is True


def test_refresh_rotates_refresh_token(authenticated_default_password_client, refresh_token):
    response = authenticated_default_password_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != refresh_token


def test_logout_all_revokes_refresh_sessions(authenticated_default_password_client):
    response = authenticated_default_password_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 204
```

- [ ] **Step 2: Run the auth integration test to verify it fails**

Run: `cd backend && pytest tests/integration/test_auth_api.py::test_login_returns_token_pair -v`
Expected: FAIL with `404 Not Found` or missing auth route.

- [ ] **Step 3: Implement login, refresh, logout, logout-all, and change-password**

```python
# backend/app/api/routes/auth.py
from fastapi import APIRouter, Depends, status
from app.schemas.auth import LoginRequest, TokenPairResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairResponse, status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest, service: AuthService = Depends()):
    return await service.login(payload)
```

```python
# backend/app/services/auth_service.py
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4
from sqlalchemy import select
from app.schemas.auth import LoginRequest, TokenPairResponse


class AuthService:
    async def login(self, payload: LoginRequest) -> TokenPairResponse:
        statement = select(User).where(User.username == payload.username, User.is_active.is_(True))
        user = (await self.session.execute(statement)).scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise DomainUnauthorizedError(code="INVALID_CREDENTIALS", message="Invalid username or password.")

        token_pair = await self.issue_token_pair(user)
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        return token_pair

    async def issue_token_pair(self, user: User) -> TokenPairResponse:
        session_jti = str(uuid4())
        access_token = issue_access_token(user_id=user.id, username=user.username, is_superuser=user.is_superuser)
        refresh_token = issue_refresh_token(user_id=user.id, session_jti=session_jti)
        refresh_ttl_seconds = self.settings.refresh_token_ttl_days * 24 * 60 * 60
        access_ttl_seconds = self.settings.access_token_ttl_minutes * 60
        await self.refresh_store.save_refresh_session(session_jti, user.id, refresh_ttl_seconds)
        self.session.add(
            RefreshSession(
                user_id=user.id,
                jti=session_jti,
                refresh_token_hash=sha256(refresh_token.encode("utf-8")).hexdigest(),
            )
        )
        await self.session.flush()
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_ttl_seconds,
            must_change_password=user.must_change_password,
        )
```

```python
# backend/tests/conftest.py
@pytest.fixture
def db_session(test_session_factory):
    with test_session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def bootstrap_admin(db_session):
    user = User(
        username="admin",
        password_hash=hash_password("jdw112233"),
        is_active=True,
        is_superuser=True,
        must_change_password=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def refresh_token(client, bootstrap_admin):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "jdw112233"})
    return response.json()["refresh_token"]


@pytest.fixture
def authenticated_default_password_client(client, bootstrap_admin):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "jdw112233"})
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return client


@pytest.fixture
def authenticated_superuser_client(authenticated_default_password_client):
    return authenticated_default_password_client


@pytest.fixture
def authenticated_client(authenticated_default_password_client):
    return authenticated_default_password_client


@pytest.fixture
def created_role(db_session):
    role = Role(name="Maintainer", code="maintainer", description="Maintainer role", is_system=False)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return {"id": role.id, "name": role.name, "code": role.code}
```

- [ ] **Step 4: Re-run the focused auth test**

Run: `cd backend && pytest tests/integration/test_auth_api.py::test_login_returns_token_pair -v`
Expected: PASS

- [ ] **Step 5: Commit auth flow**

```bash
git add backend/app/schemas/auth.py backend/app/services/auth_service.py backend/app/api/routes/auth.py backend/app/api/router.py backend/tests/integration/test_auth_api.py
git commit -m "feat: add auth api flows"
```

## Task 6: Add Auth Dependencies and Current User Context Endpoints

**Files:**
- Create: `backend/app/security/deps.py`
- Create: `backend/app/schemas/me.py`
- Create: `backend/app/services/access_context.py`
- Create: `backend/app/api/routes/me.py`
- Create: `backend/tests/unit/services/test_access_context.py`
- Create: `backend/tests/integration/test_me_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write the failing access-context tests**

```python
# backend/tests/unit/services/test_access_context.py
from app.services.access_context import build_menu_tree


def test_build_menu_tree_returns_nested_nodes():
    tree = build_menu_tree(
        [
            {"id": 1, "parent_id": None, "name": "System"},
            {"id": 2, "parent_id": 1, "name": "Users"},
        ]
    )

    assert tree[0]["children"][0]["name"] == "Users"
```

```python
# backend/tests/integration/test_me_api.py
def test_me_access_context_returns_permissions_and_menus(authenticated_client):
    response = authenticated_client.get("/api/v1/me/access-context")

    assert response.status_code == 200
    body = response.json()
    assert "permissions" in body
    assert "menus" in body
```

- [ ] **Step 2: Run the access-context tests**

Run: `cd backend && pytest tests/unit/services/test_access_context.py tests/integration/test_me_api.py -v`
Expected: FAIL because `access_context` and `/me` routes are not implemented.

- [ ] **Step 3: Implement token dependencies, permission aggregation, and `/me` routes**

```python
# backend/app/security/deps.py
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    claims = decode_token(credentials.credentials, expected_token_type="access")
    statement = select(User).where(User.id == int(claims["sub"]), User.is_active.is_(True))
    user = (await session.execute(statement)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTHENTICATION_REQUIRED")
    request.state.current_user = user
    return user


def require_permission(permission_code: str):
    async def dependency(
        current_user: User = Depends(get_current_user),
        access_context_service: AccessContextService = Depends(),
    ) -> User:
        permission_codes = await access_context_service.get_permission_codes(current_user.id)
        if not current_user.is_superuser and permission_code not in permission_codes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")
        return current_user

    return dependency
```

```python
# backend/app/api/routes/me.py
@router.get("/access-context", response_model=AccessContextResponse)
async def get_access_context(
    current_user: User = Depends(get_current_user),
    service: AccessContextService = Depends(),
):
    return await service.get_access_context(current_user)
```

- [ ] **Step 4: Re-run the access-context tests**

Run: `cd backend && pytest tests/unit/services/test_access_context.py tests/integration/test_me_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit current-user context support**

```bash
git add backend/app/security/deps.py backend/app/schemas/me.py backend/app/services/access_context.py backend/app/api/routes/me.py backend/tests/unit/services/test_access_context.py backend/tests/integration/test_me_api.py
git commit -m "feat: add current user access context"
```

## Task 7: Implement User Management and User-Role Assignment

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/services/user_service.py`
- Create: `backend/app/api/routes/users.py`
- Create: `backend/tests/integration/test_users_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write the failing users API tests**

```python
# backend/tests/integration/test_users_api.py
def test_admin_can_create_user(authenticated_superuser_client):
    response = authenticated_superuser_client.post(
        "/api/v1/users",
        json={"username": "alice", "password": "alice123456", "nickname": "Alice"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "alice"


def test_admin_can_assign_roles(authenticated_superuser_client, created_role):
    response = authenticated_superuser_client.put(
        "/api/v1/users/2/roles",
        json={"role_ids": [created_role["id"]]},
    )

    assert response.status_code == 200
```

- [ ] **Step 2: Run the users API tests**

Run: `cd backend && pytest tests/integration/test_users_api.py -v`
Expected: FAIL with `404 Not Found`.

- [ ] **Step 3: Implement user CRUD, status changes, password reset, and role assignment**

```python
# backend/app/api/routes/users.py
router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201, dependencies=[Depends(require_permission("user:create"))])
async def create_user(payload: UserCreateRequest, service: UserService = Depends()):
    return await service.create_user(payload)
```

```python
# backend/app/services/user_service.py
async def reset_password(self, user_id: int, payload: UserResetPasswordRequest) -> None:
    user = await self._get_user_or_404(user_id)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = True
    await self.refresh_session_store.revoke_all_for_user(user.id)
```

- [ ] **Step 4: Re-run the users API tests**

Run: `cd backend && pytest tests/integration/test_users_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit user management**

```bash
git add backend/app/schemas/user.py backend/app/services/user_service.py backend/app/api/routes/users.py backend/tests/integration/test_users_api.py
git commit -m "feat: add user management api"
```

## Task 8: Implement Role, Permission, and Menu Management APIs

**Files:**
- Create: `backend/app/schemas/role.py`
- Create: `backend/app/schemas/permission.py`
- Create: `backend/app/schemas/menu.py`
- Create: `backend/app/services/rbac_service.py`
- Create: `backend/app/api/routes/roles.py`
- Create: `backend/app/api/routes/permissions.py`
- Create: `backend/app/api/routes/menus.py`
- Create: `backend/tests/integration/test_roles_api.py`
- Create: `backend/tests/integration/test_permissions_api.py`
- Create: `backend/tests/integration/test_menus_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write the failing RBAC management tests**

```python
# backend/tests/integration/test_roles_api.py
def test_admin_can_create_role(authenticated_superuser_client):
    response = authenticated_superuser_client.post(
        "/api/v1/roles",
        json={"name": "Reviewer", "code": "reviewer", "description": "Code reviewer"},
    )

    assert response.status_code == 201
```

```python
# backend/tests/integration/test_permissions_api.py
def test_admin_can_create_permission(authenticated_superuser_client):
    response = authenticated_superuser_client.post(
        "/api/v1/permissions",
        json={"name": "Create User", "code": "user:create", "resource": "user", "action": "create"},
    )

    assert response.status_code == 201
```

```python
# backend/tests/integration/test_menus_api.py
def test_admin_can_create_menu(authenticated_superuser_client):
    response = authenticated_superuser_client.post(
        "/api/v1/menus",
        json={"name": "Users", "path": "/users", "sort": 10, "visible": True},
    )

    assert response.status_code == 201
```

- [ ] **Step 2: Run the RBAC management tests**

Run: `cd backend && pytest tests/integration/test_roles_api.py tests/integration/test_permissions_api.py tests/integration/test_menus_api.py -v`
Expected: FAIL with missing routes.

- [ ] **Step 3: Implement role, permission, menu CRUD and assignment flows**

```python
# backend/app/api/routes/roles.py
@router.put("/{role_id}/permissions", dependencies=[Depends(require_permission("role:assign"))])
async def assign_permissions(role_id: int, payload: RolePermissionAssignRequest, service: RBACService = Depends()):
    return await service.assign_permissions(role_id, payload.permission_ids)
```

```python
# backend/app/services/rbac_service.py
async def create_permission(self, payload: PermissionCreateRequest) -> Permission:
    permission = Permission(**payload.model_dump(), is_system=False)
    self.session.add(permission)
    await self.session.flush()
    return permission
```

- [ ] **Step 4: Re-run the RBAC management tests**

Run: `cd backend && pytest tests/integration/test_roles_api.py tests/integration/test_permissions_api.py tests/integration/test_menus_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit RBAC management**

```bash
git add backend/app/schemas/role.py backend/app/schemas/permission.py backend/app/schemas/menu.py backend/app/services/rbac_service.py backend/app/api/routes/roles.py backend/app/api/routes/permissions.py backend/app/api/routes/menus.py backend/tests/integration/test_roles_api.py backend/tests/integration/test_permissions_api.py backend/tests/integration/test_menus_api.py
git commit -m "feat: add rbac management apis"
```

## Task 9: Enforce Invariants, Structured Errors, and Logging

**Files:**
- Create: `backend/app/schemas/common.py`
- Modify: `backend/app/core/logging.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/services/user_service.py`
- Modify: `backend/app/services/rbac_service.py`
- Modify: `backend/app/security/deps.py`
- Create: `backend/tests/integration/test_security_invariants.py`

- [ ] **Step 1: Write the failing invariant tests**

```python
# backend/tests/integration/test_security_invariants.py
def test_must_change_password_blocks_management_api(authenticated_default_password_client):
    response = authenticated_default_password_client.get("/api/v1/users")

    assert response.status_code == 403
    assert response.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_cannot_delete_last_superuser(authenticated_superuser_client):
    response = authenticated_superuser_client.patch("/api/v1/users/1/status", json={"is_active": False})

    assert response.status_code in {400, 409}
```

- [ ] **Step 2: Run the invariant tests**

Run: `cd backend && pytest tests/integration/test_security_invariants.py -v`
Expected: FAIL because invariant enforcement is incomplete.

- [ ] **Step 3: Implement structured errors, logging, and invariants**

```python
# backend/app/schemas/common.py
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


class DomainError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code


class DomainUnauthorizedError(DomainError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=401)


class DomainForbiddenError(DomainError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=403)


class DomainConflictError(DomainError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)
```

```python
# backend/app/services/user_service.py
if target_user.id == current_user.id and payload.is_active is False:
    raise DomainConflictError(code="SELF_DISABLE_FORBIDDEN", message="You cannot disable your own account.")
```

```python
# backend/app/security/deps.py
if current_user.must_change_password and request.url.path not in {
    "/api/v1/auth/change-password",
    "/api/v1/auth/logout",
    "/api/v1/auth/logout-all",
    "/api/v1/me/profile",
}:
    raise DomainForbiddenError(code="PASSWORD_CHANGE_REQUIRED", message="Password change required.")
```

- [ ] **Step 4: Re-run the invariant tests**

Run: `cd backend && pytest tests/integration/test_security_invariants.py -v`
Expected: PASS

- [ ] **Step 5: Commit guardrails and logging**

```bash
git add backend/app/schemas/common.py backend/app/core/logging.py backend/app/services/auth_service.py backend/app/services/user_service.py backend/app/services/rbac_service.py backend/app/security/deps.py backend/tests/integration/test_security_invariants.py
git commit -m "feat: enforce auth and rbac invariants"
```

## Task 10: Run Full Verification and Document Local Setup

**Files:**
- Modify: `backend/README.md`
- Modify: `backend/.env.example`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Write the failing setup documentation test**

```python
# backend/tests/unit/test_readme_smoke.py
from pathlib import Path


def test_readme_mentions_database_creation():
    content = Path("README.md").read_text()

    assert "CREATE DATABASE ai_code_reviewer;" in content
    assert "redis://localhost:6379/0" in content
```

- [ ] **Step 2: Run the documentation smoke test**

Run: `cd backend && pytest tests/unit/test_readme_smoke.py -v`
Expected: FAIL until the backend README and env example contain the required setup text.

- [ ] **Step 3: Finalize README, fixtures, and project verification commands**

```markdown
# backend/README.md
## Local setup

~~~sql
CREATE DATABASE ai_code_reviewer;
~~~

~~~bash
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
~~~

Redis URL example: `redis://localhost:6379/0`
```

```python
# backend/tests/conftest.py
@pytest.fixture
def settings_override():
    return {
        "postgres_db": "ai_code_reviewer_test",
        "redis_db": 1,
    }
```

- [ ] **Step 4: Run the full verification suite**

Run: `cd backend && pytest -v`
Expected: PASS with unit and integration suites green.

Run: `cd backend && alembic upgrade head`
Expected: PASS with the auth/RBAC schema created in PostgreSQL.

Run: `cd backend && uvicorn app.main:app --reload`
Expected: App starts and exposes `/api/v1/auth/login`.

- [ ] **Step 5: Commit the final verification pass**

```bash
git add backend/README.md backend/.env.example backend/tests/conftest.py backend/tests/unit/test_readme_smoke.py
git commit -m "docs: finalize backend setup and verification"
```

## Self-Review

Spec coverage check:

- Authentication flows are covered in Tasks 3, 4, and 5.
- Redis-backed refresh-session management is covered in Tasks 3 and 5.
- Forced password change, reset-password invalidation, and logout-all behavior are covered in Tasks 5 and 9.
- User, role, permission, and menu management are covered in Tasks 7 and 8.
- Current-user profile and access context are covered in Task 6.
- BIGINT identifiers, PostgreSQL defaults, and local setup are covered in Tasks 1, 2, and 10.
- Logging and structured errors are covered in Task 9.

Placeholder scan:

- No `TODO`, `TBD`, or deferred implementation markers remain in the tasks.
- Every task has explicit file paths, commands, and a commit checkpoint.

Type consistency check:

- All route parameters use `int`, matching the Python representation for database `BIGINT`.
- `must_change_password`, `is_superuser`, and `permission_code` naming is consistent across services, routes, and tests.
