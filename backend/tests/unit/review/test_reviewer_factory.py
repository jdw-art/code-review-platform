from __future__ import annotations

import builtins
import sys
from types import ModuleType

import pytest

import app.review.reviewer.factory as reviewer_factory


def test_build_reviewer_returns_legacy_when_backend_flag_disabled(monkeypatch) -> None:
    class FakeLegacyCodeReviewerAdapter:
        pass

    monkeypatch.setattr(
        reviewer_factory,
        "LegacyCodeReviewerAdapter",
        FakeLegacyCodeReviewerAdapter,
    )

    reviewer = reviewer_factory.build_reviewer(use_backend_reviewer=False)

    assert isinstance(reviewer, FakeLegacyCodeReviewerAdapter)


def test_build_reviewer_uses_delayed_backend_import_when_enabled(monkeypatch) -> None:
    backend_module = ModuleType("app.review.reviewer.backend_reviewer")

    class FakeBackendCodeReviewer:
        pass

    backend_module.BackendCodeReviewer = FakeBackendCodeReviewer
    monkeypatch.setitem(sys.modules, "app.review.reviewer.backend_reviewer", backend_module)

    reviewer = reviewer_factory.build_reviewer(use_backend_reviewer=True)

    assert isinstance(reviewer, FakeBackendCodeReviewer)


def test_build_reviewer_raises_clear_error_when_backend_reviewer_unavailable(
    monkeypatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.review.reviewer.backend_reviewer":
            raise ModuleNotFoundError(
                "No module named 'app.review.reviewer.backend_reviewer'",
                name=name,
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="Backend reviewer is not available yet"):
        reviewer_factory.build_reviewer(use_backend_reviewer=True)
