from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.review.llm.provider import ReviewerLLMConfig, load_reviewer_llm_config
from app.review.reviewer.prompt_builder import ReviewPromptBuilder
from app.review.reviewer.protocol import ReviewRequest


class _OpenAICompatibleCompletionClient:
    def __init__(self, client: Any, *, model: str) -> None:
        self._client = client
        self._model = model

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return str(response.choices[0].message.content or "")


class _AnthropicCompletionClient:
    def __init__(self, client: Any, *, model: str) -> None:
        self._client = client
        self._model = model

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        system_prompt = "\n\n".join(
            item["content"] for item in messages if item.get("role") == "system"
        )
        user_prompt = "\n\n".join(
            item["content"] for item in messages if item.get("role") != "system"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        first_block = response.content[0] if response.content else None
        return str(getattr(first_block, "text", "") or "")


class _OllamaCompletionClient:
    def __init__(self, client: Any, *, model: str) -> None:
        self._client = client
        self._model = model

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        response = self._client.chat(
            model=self._model,
            messages=messages,
        )
        message = response.get("message", {}) if isinstance(response, dict) else {}
        return self._extract_content(str(message.get("content") or ""))

    @staticmethod
    def _extract_content(content: str) -> str:
        if "<think>" in content and "</think>" not in content:
            return "COT ABORT!"
        if "<think>" not in content and "</think>" in content:
            return content.split("</think>", 1)[1].strip()
        if re.search(r"<think>.*?</think>", content, re.DOTALL):
            return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content


def _missing_env_error(config: ReviewerLLMConfig, missing_keys: list[str]) -> RuntimeError:
    missing = ", ".join(missing_keys)
    return RuntimeError(
        f"Provider {config.provider!r} is missing required environment variable(s): {missing}."
    )


def build_llm_client(config: ReviewerLLMConfig) -> Any:
    missing_keys = [
        env_name
        for env_name in config.required_env
        if not os.getenv(env_name)
    ]
    if missing_keys:
        raise _missing_env_error(config, missing_keys)

    if config.provider in {"openai", "deepseek", "qwen"}:
        from openai import OpenAI  # noqa: PLC0415

        return _OpenAICompatibleCompletionClient(
            OpenAI(
                api_key=config.api_key,
                base_url=config.api_base_url,
            ),
            model=str(config.model),
        )

    if config.provider == "anthropic":
        from anthropic import Anthropic  # noqa: PLC0415

        http_client = httpx.Client()
        kwargs: dict[str, object] = {
            "api_key": config.api_key,
            "http_client": http_client,
        }
        if config.api_base_url:
            kwargs["base_url"] = config.api_base_url
        return _AnthropicCompletionClient(
            Anthropic(**kwargs),
            model=str(config.model),
        )

    if config.provider == "zhipuai":
        from zhipuai import ZhipuAI  # noqa: PLC0415

        return _OpenAICompatibleCompletionClient(
            ZhipuAI(api_key=config.api_key),
            model=str(config.model),
        )

    if config.provider == "ollama":
        from ollama import Client  # noqa: PLC0415

        return _OllamaCompletionClient(
            Client(host=config.api_base_url),
            model=str(config.model),
        )

    raise RuntimeError(f"Unsupported reviewer provider: {config.provider}")


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
            diffs_text=str(request.changes),
            commits_text=commits_text,
        )
        return self.client.completions(messages=messages).strip()

    @staticmethod
    def parse_score(review_text: str) -> int:
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text or "")
        return int(match.group(1)) if match else 0
