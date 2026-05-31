from __future__ import annotations

import os
import asyncio
from pathlib import Path

from app.workers import review_worker


def test_build_review_queue_service_uses_explicit_runtime_dependencies(monkeypatch) -> None:
    sentinel_settings = object()
    sentinel_redis = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(review_worker, "get_settings", lambda: sentinel_settings)
    monkeypatch.setattr(review_worker, "get_review_queue_redis_client", lambda: sentinel_redis)

    def fake_get_review_queue_service(*, settings, redis_client):
        captured["settings"] = settings
        captured["redis_client"] = redis_client
        return "queue-service"

    monkeypatch.setattr(review_worker, "get_review_queue_service", fake_get_review_queue_service)

    result = review_worker.build_review_queue_service()

    assert result == "queue-service"
    assert captured == {
        "settings": sentinel_settings,
        "redis_client": sentinel_redis,
    }


def test_prepare_codereview_runtime_sets_default_log_file_and_cwd(monkeypatch, tmp_path) -> None:
    codereview_dir = tmp_path / "codereview"
    monkeypatch.setattr(review_worker, "_get_codereview_dir", lambda: codereview_dir)
    monkeypatch.delenv("LOG_FILE", raising=False)

    result = review_worker._prepare_codereview_runtime()

    assert result == codereview_dir
    assert Path(os.environ["LOG_FILE"]) == codereview_dir / "log/app.log"
    assert (codereview_dir / "log").is_dir()
    assert Path.cwd() == codereview_dir


def test_prepare_codereview_runtime_loads_backend_env_for_codereview(monkeypatch, tmp_path) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text(
        'LLM_PROVIDER="openai"\nOPENAI_API_KEY="test-key"\n',
        encoding="utf-8",
    )
    codereview_dir = tmp_path / "codereview"
    codereview_dir.mkdir()

    monkeypatch.setattr(review_worker, "BACKEND_DIR", backend_dir)
    monkeypatch.setattr(review_worker, "_get_codereview_dir", lambda: codereview_dir)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    review_worker._prepare_codereview_runtime()

    assert os.environ["LLM_PROVIDER"] == "openai"
    assert os.environ["OPENAI_API_KEY"] == "test-key"


def test_build_review_execution_service_prepares_codereview_runtime_before_adapters(monkeypatch) -> None:
    steps: list[str] = []

    def fake_prepare() -> None:
        steps.append("prepare")

    class FakeAdapterRegistry:
        def __init__(self) -> None:
            steps.append("adapter")

    class FakeReviewer:
        def __init__(self) -> None:
            steps.append("reviewer")

    monkeypatch.setattr(review_worker, "_prepare_codereview_runtime", fake_prepare)
    monkeypatch.setattr(review_worker, "IntegrationAdapterRegistry", FakeAdapterRegistry)
    monkeypatch.setattr(review_worker, "LegacyCodeReviewerAdapter", FakeReviewer)
    monkeypatch.setattr(review_worker, "ReviewCommentService", lambda: object())
    monkeypatch.setattr(review_worker, "ReviewNotificationService", lambda: object())

    review_worker.build_review_execution_service(session=object())

    assert steps[0] == "prepare"


def test_resolve_maybe_awaitable_reuses_current_event_loop() -> None:
    async def sample() -> str:
        return "ok"

    loop = asyncio.new_event_loop()
    try:
        assert review_worker._resolve_maybe_awaitable(sample(), loop=loop) == "ok"
    finally:
        loop.close()
