from __future__ import annotations

from typing import Any

from app.review.reviewer.protocol import ReviewRequest


class LegacyCodeReviewerAdapter:
    """Bridge backend worker execution to the existing codereview LLM reviewer."""

    def __init__(self) -> None:
        from app.workers.review_worker import _ensure_codereview_on_path  # noqa: PLC0415

        _ensure_codereview_on_path()
        from biz.utils.code_reviewer import CodeReviewer  # noqa: PLC0415

        self._reviewer = CodeReviewer()

    def review(self, request: ReviewRequest | None = None, /, **kwargs: Any) -> str:
        if request is None:
            request = ReviewRequest(
                record=kwargs.get("record"),
                changes=list(kwargs.get("changes", [])),
                commits=list(kwargs.get("commits", [])),
            )
        commits_text = ";".join(
            str(message).strip()
            for message in (
                commit.get("message")
                for commit in request.commits
                if isinstance(commit, dict)
            )
            if message
        )
        return self._reviewer.review_and_strip_code(str(request.changes), commits_text)

    def parse_score(self, review_text: str) -> int:
        return self._reviewer.parse_review_score(review_text)
