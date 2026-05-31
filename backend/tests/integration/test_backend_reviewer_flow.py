import app.workers.review_worker as review_worker


def test_build_review_execution_service_uses_backend_reviewer_by_default(monkeypatch) -> None:
    calls: list[str] = []

    class FakeAdapterRegistry:
        def __init__(self) -> None:
            pass

    def fake_load_backend_env_compat() -> None:
        return None

    def fake_build_reviewer():
        calls.append("called")
        return object()

    monkeypatch.setattr(review_worker, "IntegrationAdapterRegistry", FakeAdapterRegistry)
    monkeypatch.setattr(review_worker, "_load_backend_env_compat", fake_load_backend_env_compat)
    monkeypatch.setattr(review_worker, "build_reviewer", fake_build_reviewer)
    monkeypatch.setattr(review_worker, "ReviewCommentService", lambda: object())
    monkeypatch.setattr(review_worker, "ReviewNotificationService", lambda: object())

    service = review_worker.build_review_execution_service(session=object())

    assert service.reviewer is not None
    assert calls == ["called"]
