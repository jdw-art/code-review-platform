# AI Code Reviewer Backend

FastAPI backend scaffold for the Phase 1 auth and RBAC service.

## Local setup

1. Create a virtual environment with Python 3.12 or newer.
2. Install dependencies from `pyproject.toml`.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Override the bootstrap-only auth defaults before any shared or non-local use.

## Run

```bash
cd backend && uvicorn app.main:app --reload
```

## Tests

```bash
cd backend && pytest
```
