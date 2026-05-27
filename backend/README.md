# AI Code Reviewer Backend

FastAPI backend scaffold for the Phase 1 auth and RBAC service.

## Local setup

1. Create the project database in PostgreSQL.

```sql
CREATE DATABASE ai_code_reviewer;
```

2. Create a virtual environment with Python 3.12 or newer.
3. Install dependencies from `pyproject.toml`.
4. Copy `.env.example` to `.env`.
5. Run the schema migration.

```bash
cd backend
alembic upgrade head
```

6. Override the bootstrap-only auth defaults before any shared or non-local use.

Default local services:

- PostgreSQL: `postgresql://postgres:postgres@localhost:5432/ai_code_reviewer`
- Redis: `redis://localhost:6379/0`
- Bootstrap admin: `admin / jdw112233`

## Run

```bash
cd backend
uvicorn app.main:app --reload
```

The API will expose authentication routes under `/api/v1/auth`, including `/api/v1/auth/login`.

## Tests

```bash
cd backend
pytest
```
