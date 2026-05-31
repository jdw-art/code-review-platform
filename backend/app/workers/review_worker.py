from __future__ import annotations

import asyncio
import inspect
import os
import sys
import time
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_DIR
from app.db.session import SessionLocal
from app.integrations import INTEGRATION_ADAPTERS
from app.services.review_comment_service import ReviewCommentService
from app.services.review_execution_service import ReviewExecutionService
from app.services.review_notification_service import ReviewNotificationService
from app.services.auth_service import get_settings
from app.services.review_queue_service import (
    get_review_queue_redis_client,
    get_review_queue_service,
)


def _get_codereview_dir() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "codereview"


def _load_backend_env_for_codereview() -> None:
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue

        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[env_key] = value


def _prepare_codereview_runtime() -> Path:
    codereview_dir = _get_codereview_dir()
    codereview_path = str(codereview_dir)
    if codereview_path not in sys.path:
        sys.path.insert(0, codereview_path)
    _load_backend_env_for_codereview()
    if not os.getenv("LOG_FILE"):
        log_dir = codereview_dir / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        os.environ["LOG_FILE"] = str(log_dir / "app.log")
    os.chdir(codereview_dir)
    return codereview_dir


def _ensure_codereview_on_path() -> None:
    _prepare_codereview_runtime()


class LegacyCodeReviewerAdapter:
    """Bridge backend worker execution to the existing codereview LLM reviewer."""

    def __init__(self) -> None:
        _ensure_codereview_on_path()
        from biz.utils.code_reviewer import CodeReviewer  # noqa: PLC0415

        self._reviewer = CodeReviewer()

    def review(
        self,
        record: Any,
        changes: list[dict[str, Any]],
        commits: list[dict[str, Any]],
    ) -> str:
        del record
        commits_text = ";".join(
            str(message).strip()
            for message in (
                commit.get("message")
                for commit in commits
                if isinstance(commit, dict)
            )
            if message
        )
        return self._reviewer.review_and_strip_code(str(changes), commits_text)

    def parse_score(self, review_text: str) -> int:
        return self._reviewer.parse_review_score(review_text)


class IntegrationAdapterRegistry:
    def __init__(self) -> None:
        self._adapters = {
            platform_type: adapter_class()
            for platform_type, adapter_class in INTEGRATION_ADAPTERS.items()
        }

    def get(self, platform_type: str) -> Any:
        return self._adapters[platform_type]


def build_review_execution_service(*, session) -> ReviewExecutionService:
    _prepare_codereview_runtime()
    return ReviewExecutionService(
        session=session,
        adapter_registry=IntegrationAdapterRegistry(),
        reviewer=LegacyCodeReviewerAdapter(),
        comment_service=ReviewCommentService(),
        notification_service=ReviewNotificationService(),
    )


def build_review_queue_service():
    return get_review_queue_service(
        settings=get_settings(),
        redis_client=get_review_queue_redis_client(),
    )


def _resolve_maybe_awaitable(
    value: Any,
    *,
    loop: asyncio.AbstractEventLoop | None = None,
) -> Any:
    if inspect.isawaitable(value):
        if loop is None:
            return asyncio.run(value)
        return loop.run_until_complete(value)
    return value


def run_single_review_job(
    queue_service,
    session,
    *,
    loop: asyncio.AbstractEventLoop | None = None,
) -> bool:
    message = _resolve_maybe_awaitable(queue_service.dequeue(), loop=loop)
    if message is None:
        return False

    service = build_review_execution_service(session=session)
    service.execute(
        review_record_id=message.review_record_id,
        attempt=message.attempt,
    )
    return True


def main() -> None:
    queue_service = build_review_queue_service()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        while True:
            session = SessionLocal()
            try:
                processed = run_single_review_job(queue_service, session, loop=loop)
            finally:
                session.close()
            if not processed:
                time.sleep(1.0)
    finally:
        close = getattr(queue_service.redis, "aclose", None)
        if callable(close):
            loop.run_until_complete(close())
        loop.close()


if __name__ == "__main__":
    main()
