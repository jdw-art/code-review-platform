from __future__ import annotations

from app.review.reviewer.legacy_reviewer import LegacyCodeReviewerAdapter
from app.review.reviewer.protocol import ReviewerProtocol


def build_reviewer(*, use_backend_reviewer: bool) -> ReviewerProtocol:
    if use_backend_reviewer:
        try:
            from app.review.reviewer.backend_reviewer import BackendCodeReviewer  # noqa: PLC0415
        except ModuleNotFoundError as exc:
            if exc.name != "app.review.reviewer.backend_reviewer":
                raise
            raise RuntimeError(
                "Backend reviewer is not available yet. "
                "Implement app.review.reviewer.backend_reviewer.BackendCodeReviewer first."
            ) from exc

        return BackendCodeReviewer()
    return LegacyCodeReviewerAdapter()
