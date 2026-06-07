from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.llm.provider import LLMConfig


_shared_httpx_client: httpx.Client | Any | None = None


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
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "assistant" if item.get("role") == "assistant" else "user",
                    "content": str(item.get("content", "")),
                }
                for item in messages
                if item.get("role") != "system"
            ],
        )
        parts = [
            str(getattr(block, "text", "") or "")
            for block in (response.content or [])
            if getattr(block, "text", None)
        ]
        return "".join(parts)


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


def _missing_env_error(config: LLMConfig, missing_keys: list[str]) -> RuntimeError:
    missing = ", ".join(missing_keys)
    return RuntimeError(
        f"Provider {config.provider!r} is missing required environment variable(s): {missing}."
    )


def _get_shared_httpx_client() -> httpx.Client | Any:
    global _shared_httpx_client
    if _shared_httpx_client is None:
        _shared_httpx_client = httpx.Client()
    return _shared_httpx_client


def build_llm_client(config: LLMConfig) -> Any:
    missing_keys = [
        env_name
        for env_name in config.required_env
        if not _config_has_required_value(config, env_name)
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

        kwargs: dict[str, object] = {
            "api_key": config.api_key,
            "http_client": _get_shared_httpx_client(),
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

    raise RuntimeError(f"Unsupported LLM provider: {config.provider}")


def _config_has_required_value(config: LLMConfig, env_name: str) -> bool:
    if env_name.endswith("_API_KEY"):
        return bool(config.api_key)
    if env_name.endswith("_API_BASE_URL"):
        return bool(config.api_base_url)
    if env_name.endswith("_API_MODEL"):
        return bool(config.model)
    return bool(os.getenv(env_name))
