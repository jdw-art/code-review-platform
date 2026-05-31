from __future__ import annotations

import asyncio
import os

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


def test_load_backend_env_compat_reads_backend_env_without_overriding_existing_values(
    monkeypatch,
    tmp_path,
) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text(
        'LLM_PROVIDER="anthropic"\nOPENAI_API_KEY="file-openai-key"\nSUPPORTED_EXTENSIONS=".py,.ts"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(review_worker, "BACKEND_DIR", backend_dir)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "existing-openai-key")
    monkeypatch.delenv("SUPPORTED_EXTENSIONS", raising=False)

    review_worker._load_backend_env_compat()

    assert os.environ["LLM_PROVIDER"] == "anthropic"
    assert os.environ["OPENAI_API_KEY"] == "existing-openai-key"
    assert os.environ["SUPPORTED_EXTENSIONS"] == ".py,.ts"


def test_load_backend_env_compat_ignores_missing_env_file(monkeypatch, tmp_path) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    monkeypatch.setattr(review_worker, "BACKEND_DIR", backend_dir)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    review_worker._load_backend_env_compat()

    assert "LLM_PROVIDER" not in os.environ


def test_build_review_execution_service_loads_backend_env_before_building_reviewer(monkeypatch) -> None:
    steps: list[str] = []

    def fake_load_backend_env_compat() -> None:
        steps.append("load-env")

    class FakeAdapterRegistry:
        def __init__(self) -> None:
            steps.append("adapter")

    def fake_build_reviewer():
        steps.append("reviewer")
        return object()

    monkeypatch.setattr(review_worker, "IntegrationAdapterRegistry", FakeAdapterRegistry)
    monkeypatch.setattr(review_worker, "build_reviewer", fake_build_reviewer)
    monkeypatch.setattr(review_worker, "ReviewCommentService", lambda: object())
    monkeypatch.setattr(review_worker, "ReviewNotificationService", lambda: object())
    monkeypatch.setattr(
        review_worker,
        "_load_backend_env_compat",
        fake_load_backend_env_compat,
    )

    review_worker.build_review_execution_service(session=object())

    assert steps[0] == "load-env"
    assert "reviewer" in steps


def test_resolve_maybe_awaitable_reuses_current_event_loop() -> None:
    async def sample() -> str:
        return "ok"

    loop = asyncio.new_event_loop()
    try:
        assert review_worker._resolve_maybe_awaitable(sample(), loop=loop) == "ok"
    finally:
        loop.close()
