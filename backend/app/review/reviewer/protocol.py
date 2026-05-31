from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ReviewRequest:
    record: Any
    changes: list[dict[str, Any]]
    commits: list[dict[str, Any]]


class ReviewerProtocol(Protocol):
    def review(self, request: ReviewRequest) -> str: ...

    def parse_score(self, review_text: str) -> int: ...
