from __future__ import annotations

import os
from dataclasses import dataclass


PROVIDER_ENV_CONFIG: dict[str, dict[str, object]] = {
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "api_base_url_env": "ANTHROPIC_API_BASE_URL",
        "model_env": "ANTHROPIC_API_MODEL",
        "default_api_base_url": None,
        "default_model": "claude-sonnet-4-5-20250929",
        "required_env": ("ANTHROPIC_API_KEY",),
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "api_base_url_env": "OPENAI_API_BASE_URL",
        "model_env": "OPENAI_API_MODEL",
        "default_api_base_url": None,
        "default_model": "gpt-4o-mini",
        "required_env": ("OPENAI_API_KEY",),
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "api_base_url_env": "DEEPSEEK_API_BASE_URL",
        "model_env": "DEEPSEEK_API_MODEL",
        "default_api_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "required_env": ("DEEPSEEK_API_KEY",),
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "api_base_url_env": "QWEN_API_BASE_URL",
        "model_env": "QWEN_API_MODEL",
        "default_api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-coder-plus",
        "required_env": ("QWEN_API_KEY",),
    },
    "zhipuai": {
        "api_key_env": "ZHIPUAI_API_KEY",
        "api_base_url_env": None,
        "model_env": "ZHIPUAI_API_MODEL",
        "default_api_base_url": None,
        "default_model": "GLM-4-Flash",
        "required_env": ("ZHIPUAI_API_KEY",),
    },
    "ollama": {
        "api_key_env": None,
        "api_base_url_env": "OLLAMA_API_BASE_URL",
        "model_env": "OLLAMA_API_MODEL",
        "default_api_base_url": "http://127.0.0.1:11434",
        "default_model": "deepseek-r1-8k:14b",
        "required_env": (),
    },
}


@dataclass(slots=True)
class ReviewerLLMConfig:
    provider: str
    api_key: str | None
    api_base_url: str | None
    model: str | None
    required_env: tuple[str, ...] = ()


def load_reviewer_llm_config() -> ReviewerLLMConfig:
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    provider_config = PROVIDER_ENV_CONFIG.get(provider)
    if provider_config is None:
        supported = ", ".join(sorted(PROVIDER_ENV_CONFIG))
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER={provider!r}. Supported providers: {supported}."
        )

    api_key_env = provider_config["api_key_env"]
    api_base_url_env = provider_config["api_base_url_env"]
    model_env = provider_config["model_env"]

    api_key = os.getenv(api_key_env) if isinstance(api_key_env, str) else None
    api_base_url = None
    if isinstance(api_base_url_env, str):
        api_base_url = os.getenv(
            api_base_url_env,
            provider_config["default_api_base_url"],
        )
    model = os.getenv(model_env, str(provider_config["default_model"]))

    return ReviewerLLMConfig(
        provider=provider,
        api_key=api_key,
        api_base_url=api_base_url,
        model=model,
        required_env=tuple(provider_config["required_env"]),
    )
