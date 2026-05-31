from __future__ import annotations

from app.review.reviewer.protocol import ReviewerProtocol


def build_reviewer() -> ReviewerProtocol:
    from app.review.reviewer.backend_reviewer import BackendCodeReviewer  # noqa: PLC0415

    return BackendCodeReviewer()
