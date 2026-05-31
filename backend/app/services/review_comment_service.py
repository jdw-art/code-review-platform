from __future__ import annotations

from typing import Any

from app.db.models import ReviewRecord


class ReviewCommentService:
    """负责将审查结果回写到代码托管平台。"""

    def deliver(self, *, adapter: Any, record: ReviewRecord, review_result: str) -> None:
        adapter.publish_review_comment(
            record=record,
            review_result=self._format_review_comment(review_result),
        )

    @staticmethod
    def _format_review_comment(review_result: str) -> str:
        return f"Auto Review Result: \n{review_result}"
