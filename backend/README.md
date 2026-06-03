# AI Code Reviewer Backend

FastAPI backend for the integrated AI code review flow. The backend now unifies:

- GitLab / GitHub webhook ingestion
- PostgreSQL review record persistence
- Redis-backed review queue
- review worker execution
- review comment delivery
- notification delivery
- daily report generation
- repository assistant session / run / snapshot / SSE flow

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

Recommended local development path:

- Run `uvicorn app.main:app --reload` as the primary entrypoint.
- Set `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1` to let the backend auto-start the review worker in development.
- The backend native reviewer is the only runtime path.

Manual worker entrypoints are still available when you want explicit process control:

```bash
cd backend
python -m app.workers.review_worker
python -m app.workers.report_worker
```

The API exposes authentication routes under `/api/v1/auth`, including `/api/v1/auth/login`.

## Repository Assistant

The backend now exposes a project-scoped, read-only repository assistant for reducing codebase comprehension cost in complex repos.

Current boundaries:

- read-only tools only: `list_files`, `read_file`, `search`, `get_project_overview`, `get_recent_commits`
- no shell execution
- no file writes
- no patch / checkpoint / resume
- session, message, run, event, artifact, and snapshot state persist in PostgreSQL

Primary routes:

- `GET /api/v1/projects/{project_id}/agent/sessions`
- `POST /api/v1/projects/{project_id}/agent/sessions`
- `GET /api/v1/agent/sessions/{session_id}`
- `GET /api/v1/agent/sessions/{session_id}/messages`
- `POST /api/v1/agent/sessions/{session_id}/messages`
- `GET /api/v1/agent/sessions/{session_id}/stream`
- `POST /api/v1/agent/sessions/{session_id}/snapshot/refresh`
- `GET /api/v1/agent/runs/{run_id}`

Notes:

- the first backend version uses a lightweight repository snapshot plus on-demand file reads
- SSE replay supports `Last-Event-ID` and `since_event_id`
- browser EventSource can authenticate through the regular bearer header path or `access_token` query fallback

## Webhook Endpoints

- GitLab: `POST /api/v1/integrations/webhooks/gitlab`
- GitHub: `POST /api/v1/integrations/webhooks/github`

## Required Environment Variables

Backend config:

- `AI_CODE_REVIEWER_REVIEW_QUEUE_NAME`
- `AI_CODE_REVIEWER_REVIEW_LOCK_PREFIX`
- `AI_CODE_REVIEWER_REVIEW_MAX_RETRIES`
- `AI_CODE_REVIEWER_REVIEW_LOCK_TTL_SECONDS`
- `AI_CODE_REVIEWER_REPORT_CRONTAB_EXPRESSION`

Platform access:

- `GITLAB_ACCESS_TOKEN`
- `GITLAB_URL`
- `GITHUB_ACCESS_TOKEN`
- `GITHUB_URL`
- `GITHUB_API_URL`

Compatibility environment variables still supported by backend runtime:

- `SUPPORTED_EXTENSIONS`
- `MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED`
- `PUSH_REVIEW_ENABLED`
- `REPORT_CRONTAB_EXPRESSION`

LLM and review generation:

- `LLM_PROVIDER`
- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / other provider credentials used by the backend reviewer

Notification compatibility:

- `DINGTALK_ENABLED`
- `DINGTALK_WEBHOOK_URL`
- `DINGTALK_SECRET_ENABLED`
- `DINGTALK_SECRET`
- `WECOM_ENABLED`
- `WECOM_WEBHOOK_URL`
- `FEISHU_ENABLED`
- `FEISHU_WEBHOOK_URL`
- `EXTRA_WEBHOOK_ENABLED`
- `EXTRA_WEBHOOK_URL`

## Operational Checklist

- Confirm webhook endpoints are reachable from GitLab / GitHub.
- Confirm Redis is available before starting `app.workers.review_worker`.
- Confirm PostgreSQL migrations are applied before ingesting webhook events.
- Confirm platform access tokens can read MR / PR changes and write comments.
- Confirm notification env vars or project default bot config are set before enabling delivery.
- Confirm LLM provider env vars are present before starting the review worker.

## Tests

```bash
cd backend
pytest
```

## Verification Script

Run `python scripts/verify_full_review_flow.py` from `backend/` to perform a real GitHub push-based end-to-end validation of the review pipeline. The script writes a Markdown report under `docs/verification/`.

Run `python scripts/verify_pico_online_agent_flow.py` from `backend/` to validate the repository assistant with a real 3-turn persisted conversation flow. The script checks:

- final assistant output exists for each turn
- SSE/event formatting is replayable
- tool calls are emitted and persisted
- prompt metadata contains section assembly details
- memory is updated across turns
- later turns can reference earlier turns without losing context
