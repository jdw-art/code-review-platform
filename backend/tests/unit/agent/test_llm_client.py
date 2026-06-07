from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.llm.client_factory as client_factory_module
from app.llm.client_factory import _AnthropicCompletionClient, build_llm_client
from app.llm.provider import LLMConfig, load_llm_config


@pytest.mark.parametrize(
    ("provider", "env_vars", "expected"),
    [
        (
            "anthropic",
            {
                "ANTHROPIC_API_KEY": "anthropic-key",
                "ANTHROPIC_API_BASE_URL": "https://anthropic.example.com",
                "ANTHROPIC_API_MODEL": "claude-custom",
            },
            ("anthropic-key", "https://anthropic.example.com", "claude-custom"),
        ),
        (
            "openai",
            {
                "OPENAI_API_KEY": "openai-key",
                "OPENAI_API_BASE_URL": "https://openai.example.com/v1",
                "OPENAI_API_MODEL": "gpt-4o-mini",
            },
            ("openai-key", "https://openai.example.com/v1", "gpt-4o-mini"),
        ),
        (
            "deepseek",
            {
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_API_BASE_URL": "https://deepseek.example.com",
                "DEEPSEEK_API_MODEL": "deepseek-chat",
            },
            ("deepseek-key", "https://deepseek.example.com", "deepseek-chat"),
        ),
        (
            "qwen",
            {
                "QWEN_API_KEY": "qwen-key",
                "QWEN_API_BASE_URL": "https://qwen.example.com",
                "QWEN_API_MODEL": "qwen-coder-plus",
            },
            ("qwen-key", "https://qwen.example.com", "qwen-coder-plus"),
        ),
        (
            "zhipuai",
            {
                "ZHIPUAI_API_KEY": "zhipu-key",
                "ZHIPUAI_API_MODEL": "glm-4-flash",
            },
            ("zhipu-key", None, "glm-4-flash"),
        ),
        (
            "ollama",
            {
                "OLLAMA_API_BASE_URL": "http://127.0.0.1:11434",
                "OLLAMA_API_MODEL": "deepseek-r1-8k:14b",
            },
            (None, "http://127.0.0.1:11434", "deepseek-r1-8k:14b"),
        ),
    ],
)
def test_load_llm_config_uses_existing_env_contract(
    monkeypatch,
    provider: str,
    env_vars: dict[str, str],
    expected: tuple[str | None, str | None, str | None],
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config = load_llm_config()

    assert config.provider == provider
    assert (config.api_key, config.api_base_url, config.model) == expected


def test_build_llm_client_raises_for_missing_required_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        build_llm_client(
            LLMConfig(
                provider="anthropic",
                api_key=None,
                api_base_url=None,
                model="claude-sonnet-4-5-20250929",
                required_env=("ANTHROPIC_API_KEY",),
            )
        )


def test_build_llm_client_accepts_explicit_config_value_without_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakeHTTPXClient:
        pass

    class FakeAnthropic:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(client_factory_module.httpx, "Client", FakeHTTPXClient)
    monkeypatch.setattr(client_factory_module, "_shared_httpx_client", None)
    monkeypatch.setitem(__import__("sys").modules, "anthropic", type("M", (), {"Anthropic": FakeAnthropic})())

    client = build_llm_client(
        LLMConfig(
            provider="anthropic",
            api_key="injected-key",
            api_base_url=None,
            model="claude-sonnet-4-5-20250929",
            required_env=("ANTHROPIC_API_KEY",),
        )
    )

    assert isinstance(client, _AnthropicCompletionClient)


def test_anthropic_completion_client_preserves_message_roles_and_joins_text_blocks() -> None:
    captured: dict[str, object] = {}

    class FakeMessagesAPI:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="thinking", text=""),
                    SimpleNamespace(type="text", text="hello"),
                    SimpleNamespace(type="text", text=" world"),
                ]
            )

    class FakeAnthropicClient:
        def __init__(self) -> None:
            self.messages = FakeMessagesAPI()

    client = _AnthropicCompletionClient(FakeAnthropicClient(), model="claude-test")

    result = client.completions(
        messages=[
            {"role": "system", "content": "system rules"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "second question"},
        ]
    )

    assert result == "hello world"
    assert captured["system"] == "system rules"
    assert captured["messages"] == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second question"},
    ]
