from __future__ import annotations

from typing import Any

from app.review.reviewer.protocol import ReviewRequest


class LegacyCodeReviewerAdapter:
    """Temporary fallback bridge for the legacy codereview reviewer path."""

    def __init__(self) -> None:
        try:
            from biz.utils.code_reviewer import CodeReviewer  # noqa: PLC0415
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Legacy reviewer fallback is unavailable without the legacy codereview runtime. "
                "Use AI_CODE_REVIEWER_USE_BACKEND_REVIEWER=1 to keep the backend-native path enabled."
            ) from exc

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
