from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Role, User
from app.db.session import get_db
from app.main import app
from app.security.passwords import hash_password

try:
    from app.services.auth_service import get_refresh_session_store
except ImportError:  # pragma: no cover - used during TDD red phase before service exists.
    get_refresh_session_store = None

POSTGRES_ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
POSTGRES_TEST_DSN_TEMPLATE = "postgresql+psycopg://postgres:postgres@localhost:5432/{db_name}"


class InMemoryRefreshSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, int] = {}
        self.user_index: dict[int, set[str]] = {}

    async def save_refresh_session(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        del ttl_seconds
        self.sessions[jti] = user_id
        self.user_index.setdefault(user_id, set()).add(jti)

    async def get_user_id_for_session(self, jti: str) -> int | None:
        return self.sessions.get(jti)

    async def list_user_session_jtis(self, user_id: int) -> set[str]:
        return set(self.user_index.get(user_id, set()))

    async def revoke_refresh_session(self, jti: str, user_id: int) -> None:
        self.sessions.pop(jti, None)
        session_jtis = self.user_index.get(user_id)
        if not session_jtis:
            return
        session_jtis.discard(jti)
        if not session_jtis:
            self.user_index.pop(user_id, None)

    async def revoke_all_user_sessions(self, user_id: int) -> int:
        session_jtis = self.user_index.pop(user_id, set())
        for jti in session_jtis:
            self.sessions.pop(jti, None)
        return len(session_jtis)


@contextmanager
def postgres_test_session_factory() -> Generator[sessionmaker[Session], None, None]:
    db_name = f"auth_test_{uuid4().hex[:8]}"

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
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name))
            )


@pytest.fixture
def test_session_factory() -> Generator[sessionmaker[Session], None, None]:
    with postgres_test_session_factory() as session_factory:
        yield session_factory


@pytest.fixture
def db_session(test_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with test_session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def refresh_session_store() -> InMemoryRefreshSessionStore:
    return InMemoryRefreshSessionStore()


@pytest.fixture
def client(
    test_session_factory: sessionmaker[Session],
    refresh_session_store: InMemoryRefreshSessionStore,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    if get_refresh_session_store is not None:
        app.dependency_overrides[get_refresh_session_store] = lambda: refresh_session_store

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


@pytest.fixture
def bootstrap_admin(db_session: Session) -> User:
    user = User(
        username="admin",
        password_hash=hash_password("jdw112233"),
        is_active=True,
        is_superuser=True,
        must_change_password=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def refresh_token(client: TestClient, bootstrap_admin: User) -> str:
    del bootstrap_admin
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    return response.json()["refresh_token"]


@pytest.fixture
def authenticated_default_password_client(
    client: TestClient,
    bootstrap_admin: User,
) -> TestClient:
    del bootstrap_admin
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "jdw112233"},
    )
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return client


@pytest.fixture
def authenticated_superuser_client(
    authenticated_default_password_client: TestClient,
) -> TestClient:
    return authenticated_default_password_client


@pytest.fixture
def authenticated_client(authenticated_default_password_client: TestClient) -> TestClient:
    return authenticated_default_password_client


@pytest.fixture
def created_role(db_session: Session) -> dict[str, int | str]:
    role = Role(
        name="Maintainer",
        code="maintainer",
        description="Maintainer role",
        is_system=False,
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return {"id": role.id, "name": role.name, "code": role.code}
