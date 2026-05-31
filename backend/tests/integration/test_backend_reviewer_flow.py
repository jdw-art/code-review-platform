from __future__ import annotations

import app.workers.review_worker as review_worker


def test_build_review_execution_service_uses_backend_reviewer_when_flag_enabled(
    monkeypatch,
) -> None:
    calls: list[bool] = []

    class FakeAdapterRegistry:
        def __init__(self) -> None:
            pass

    def fake_prepare() -> None:
        return None

    def fake_build_reviewer(*, use_backend_reviewer: bool):
        calls.append(use_backend_reviewer)
        return object()

    monkeypatch.setattr(review_worker, "_prepare_codereview_runtime", fake_prepare)
    monkeypatch.setattr(review_worker, "IntegrationAdapterRegistry", FakeAdapterRegistry)
    monkeypatch.setattr(
        review_worker,
        "get_settings",
        lambda: type("Settings", (), {"use_backend_reviewer": True})(),
    )
    monkeypatch.setattr(review_worker, "build_reviewer", fake_build_reviewer)
    monkeypatch.setattr(review_worker, "ReviewCommentService", lambda: object())
    monkeypatch.setattr(review_worker, "ReviewNotificationService", lambda: object())

    service = review_worker.build_review_execution_service(session=object())

    assert service.reviewer is not None
    assert calls == [True]
