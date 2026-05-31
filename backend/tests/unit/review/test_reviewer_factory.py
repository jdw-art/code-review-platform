import sys
from types import ModuleType

import app.review.reviewer.factory as reviewer_factory


def test_build_reviewer_uses_backend_reviewer(monkeypatch) -> None:
    backend_module = ModuleType("app.review.reviewer.backend_reviewer")

    class FakeBackendCodeReviewer:
        pass

    backend_module.BackendCodeReviewer = FakeBackendCodeReviewer
    monkeypatch.setitem(sys.modules, "app.review.reviewer.backend_reviewer", backend_module)

    reviewer = reviewer_factory.build_reviewer()

    assert isinstance(reviewer, FakeBackendCodeReviewer)
