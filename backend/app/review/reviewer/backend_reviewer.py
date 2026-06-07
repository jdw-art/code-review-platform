from __future__ import annotations

import json
import os
import re
from typing import Any

from app.review.llm.provider import ReviewerLLMConfig, load_reviewer_llm_config
from app.review.reviewer.prompt_builder import ReviewPromptBuilder
from app.review.reviewer.protocol import ReviewRequest
from app.llm.client_factory import (
    _AnthropicCompletionClient,
    _OllamaCompletionClient,
    _OpenAICompatibleCompletionClient,
    build_llm_client,
)


class BackendCodeReviewer:
    def __init__(
        self,
        *,
        client: Any | None = None,
        prompt_builder: ReviewPromptBuilder | None = None,
    ) -> None:
        self.client = client or build_llm_client(load_reviewer_llm_config())
        self.prompt_builder = prompt_builder or ReviewPromptBuilder()

    def review(self, request: ReviewRequest) -> str:
        commits_text = ";".join(
            str(message).strip()
            for message in (
                item.get("message")
                for item in request.commits
                if isinstance(item, dict)
            )
            if message
        )
        messages = self.prompt_builder.build_messages(
            style=os.getenv("REVIEW_STYLE", "professional"),
            diffs_text=self._render_changes(request.changes),
            commits_text=commits_text,
        )
        return self.client.completions(messages=messages).strip()

    @staticmethod
    def parse_score(review_text: str) -> int:
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text or "")
        return int(match.group(1)) if match else 0

    @staticmethod
    def _render_changes(changes: list[dict[str, Any]]) -> str:
        return json.dumps(changes, ensure_ascii=False, indent=2)
