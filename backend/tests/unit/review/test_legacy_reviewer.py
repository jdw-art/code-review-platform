from __future__ import annotations

import builtins

import pytest

from app.review.reviewer.legacy_reviewer import LegacyCodeReviewerAdapter


def test_legacy_reviewer_raises_clear_error_without_legacy_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "biz.utils.code_reviewer":
            raise ModuleNotFoundError(
                "No module named 'biz.utils.code_reviewer'",
                name=name,
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="legacy codereview runtime"):
        LegacyCodeReviewerAdapter()
