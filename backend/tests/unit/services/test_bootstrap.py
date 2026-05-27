from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Role, User
from app.db.models.role import SYSTEM_SUPER_ADMIN_ROLE_CODE
from app.services.bootstrap import (
    bootstrap_initial_admin,
    build_bootstrap_admin_payload,
)

POSTGRES_ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
POSTGRES_TEST_DSN_TEMPLATE = "postgresql+psycopg://postgres:postgres@localhost:5432/{db_name}"


@contextmanager
def postgres_test_session_factory() -> sessionmaker[Session]:
    db_name = f"bootstrap_test_{uuid4().hex[:8]}"

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


def make_settings() -> Settings:
    return Settings(
        bootstrap_admin_username="admin",
        bootstrap_admin_password="jdw112233",
    )


def test_bootstrap_admin_requires_password_change() -> None:
    payload = build_bootstrap_admin_payload(make_settings())

    assert payload["username"] == "admin"
    assert payload["is_superuser"] is True
    assert payload["must_change_password"] is True


def test_bootstrap_initial_admin_creates_user_role_and_link() -> None:
    with postgres_test_session_factory() as session_factory:
        bootstrap_initial_admin(
            session_factory=session_factory,
            settings=make_settings(),
        )

        with session_factory() as session:
            user = session.scalar(select(User).where(User.username == "admin"))
            role = session.scalar(
                select(Role).where(Role.code == SYSTEM_SUPER_ADMIN_ROLE_CODE)
            )

            assert user is not None
            assert role is not None
            assert user.is_superuser is True
            assert user.must_change_password is True
            assert [assigned_role.code for assigned_role in user.roles] == [
                SYSTEM_SUPER_ADMIN_ROLE_CODE
            ]


def test_bootstrap_initial_admin_is_idempotent() -> None:
    with postgres_test_session_factory() as session_factory:
        settings = make_settings()

        bootstrap_initial_admin(session_factory=session_factory, settings=settings)
        bootstrap_initial_admin(session_factory=session_factory, settings=settings)

        with session_factory() as session:
            assert session.query(User).count() == 1
            assert session.query(Role).count() == 1
            user = session.scalar(select(User).where(User.username == "admin"))
            assert user is not None
            assert len(user.roles) == 1


def test_bootstrap_initial_admin_attaches_missing_role_to_existing_user() -> None:
    with postgres_test_session_factory() as session_factory:
        settings = make_settings()

        with session_factory() as session:
            with session.begin():
                session.add(User(**build_bootstrap_admin_payload(settings)))

        bootstrap_initial_admin(session_factory=session_factory, settings=settings)

        with session_factory() as session:
            user = session.scalar(select(User).where(User.username == "admin"))
            role = session.scalar(
                select(Role).where(Role.code == SYSTEM_SUPER_ADMIN_ROLE_CODE)
            )

            assert user is not None
            assert role is not None
            assert len(user.roles) == 1
            assert user.roles[0].code == SYSTEM_SUPER_ADMIN_ROLE_CODE
