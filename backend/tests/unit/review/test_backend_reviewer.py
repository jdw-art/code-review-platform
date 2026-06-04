from __future__ import annotations

import pytest

import app.review.reviewer.backend_reviewer as backend_reviewer_module
import app.llm.client_factory as llm_client_factory_module
from app.review.llm.provider import ReviewerLLMConfig, load_reviewer_llm_config
from app.review.reviewer.backend_reviewer import BackendCodeReviewer
from app.review.reviewer.protocol import ReviewRequest


class FakePromptBuilder:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def build_messages(
        self,
        *,
        style: str,
        diffs_text: str,
        commits_text: str,
    ) -> list[dict[str, str]]:
        self.calls.append(
            {
                "style": style,
                "diffs_text": diffs_text,
                "commits_text": commits_text,
            }
        )
        return [
            {"role": "system", "content": f"style={style}"},
            {"role": "user", "content": f"{diffs_text}\n{commits_text}"},
        ]


class FakeClient:
    def __init__(self, response_text: str = "总结\n总分:88分") -> None:
        self.response_text = response_text
        self.messages: list[list[dict[str, str]]] = []

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        return self.response_text


class FakeOllamaSDKClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def chat(self, *, model: str, messages: list[dict[str, str]]) -> dict[str, object]:
        self.calls.append({"model": model, "messages": messages})
        return {"message": {"content": self.content}}


def test_load_reviewer_llm_config_defaults_to_anthropic(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_MODEL", raising=False)

    config = load_reviewer_llm_config()

    assert config.provider == "anthropic"
    assert config.api_key is None
    assert config.api_base_url is None
    assert config.model == "claude-sonnet-4-5-20250929"


def test_load_reviewer_llm_config_uses_codereview_defaults_for_ollama(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_API_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_API_MODEL", raising=False)

    config = load_reviewer_llm_config()

    assert config.provider == "ollama"
    assert config.api_key is None
    assert config.api_base_url == "http://127.0.0.1:11434"
    assert config.model == "deepseek-r1-8k:14b"
    assert config.required_env == ()


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
def test_load_reviewer_llm_config_reads_provider_specific_env_names(
    monkeypatch,
    provider: str,
    env_vars: dict[str, str],
    expected: tuple[str | None, str | None, str | None],
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    config = load_reviewer_llm_config()

    assert config.provider == provider
    assert (config.api_key, config.api_base_url, config.model) == expected


def test_backend_reviewer_default_constructor_builds_client_from_loader(monkeypatch) -> None:
    built_clients: list[ReviewerLLMConfig] = []

    monkeypatch.setattr(
        backend_reviewer_module,
        "load_reviewer_llm_config",
        lambda: ReviewerLLMConfig(
            provider="openai",
            api_key="openai-key",
            api_base_url="https://example.com/v1",
            model="gpt-4o-mini",
        ),
    )

    def fake_build_llm_client(config: ReviewerLLMConfig):
        built_clients.append(config)
        return FakeClient()

    monkeypatch.setattr(backend_reviewer_module, "build_llm_client", fake_build_llm_client)

    reviewer = BackendCodeReviewer()

    assert isinstance(reviewer.client, FakeClient)
    assert built_clients == [
        ReviewerLLMConfig(
            provider="openai",
            api_key="openai-key",
            api_base_url="https://example.com/v1",
            model="gpt-4o-mini",
        )
    ]


def test_backend_reviewer_reports_missing_required_env(monkeypatch) -> None:
    monkeypatch.setattr(
        backend_reviewer_module,
        "load_reviewer_llm_config",
        lambda: ReviewerLLMConfig(
            provider="anthropic",
            api_key=None,
            api_base_url=None,
            model="claude-sonnet-4-5-20250929",
            required_env=("ANTHROPIC_API_KEY",),
        ),
    )

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        BackendCodeReviewer()


def test_ollama_completion_client_strips_think_block() -> None:
    client = backend_reviewer_module._OllamaCompletionClient(
        FakeOllamaSDKClient("<think>internal</think>\nVisible answer"),
        model="deepseek-r1-8k:14b",
    )

    result = client.completions(messages=[{"role": "user", "content": "hi"}])

    assert result == "Visible answer"


def test_ollama_completion_client_returns_abort_when_think_not_closed() -> None:
    client = backend_reviewer_module._OllamaCompletionClient(
        FakeOllamaSDKClient("<think>internal"),
        model="deepseek-r1-8k:14b",
    )

    result = client.completions(messages=[{"role": "user", "content": "hi"}])

    assert result == "COT ABORT!"


def test_build_llm_client_passes_httpx_client_to_anthropic(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHTTPXClient:
        pass

    class FakeAnthropic:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(llm_client_factory_module.httpx, "Client", FakeHTTPXClient)
    monkeypatch.setattr(llm_client_factory_module, "_shared_httpx_client", None)
    monkeypatch.setitem(__import__("sys").modules, "anthropic", type("M", (), {"Anthropic": FakeAnthropic})())

    client = backend_reviewer_module.build_llm_client(
        ReviewerLLMConfig(
            provider="anthropic",
            api_key="anthropic-key",
            api_base_url=None,
            model="claude-sonnet-4-5-20250929",
            required_env=(),
        )
    )

    assert isinstance(client, backend_reviewer_module._AnthropicCompletionClient)
    assert captured["api_key"] == "anthropic-key"
    assert "http_client" in captured
    assert isinstance(captured["http_client"], FakeHTTPXClient)


def test_backend_reviewer_builds_messages_and_calls_client(monkeypatch) -> None:
    monkeypatch.setenv("REVIEW_STYLE", "gentle")
    prompt_builder = FakePromptBuilder()
    client = FakeClient(response_text="  总结\n总分:88分  ")
    reviewer = BackendCodeReviewer(client=client, prompt_builder=prompt_builder)

    result = reviewer.review(
        ReviewRequest(
            record=object(),
            changes=[{"new_path": "app.py", "diff": "+print('ok')"}],
            commits=[
                {"message": "feat: add login"},
                {"message": "fix: polish login"},
            ],
        )
    )

    assert result == "总结\n总分:88分"
    assert prompt_builder.calls == [
        {
            "style": "gentle",
            "diffs_text": '[\n  {\n    "new_path": "app.py",\n    "diff": "+print(\'ok\')"\n  }\n]',
            "commits_text": "feat: add login;fix: polish login",
        }
    ]
    assert client.messages == [
        [
            {"role": "system", "content": "style=gentle"},
            {
                "role": "user",
                "content": '[\n  {\n    "new_path": "app.py",\n    "diff": "+print(\'ok\')"\n  }\n]\nfeat: add login;fix: polish login',
            },
        ]
    ]


def test_backend_reviewer_parses_score_from_review_text() -> None:
    assert BackendCodeReviewer.parse_score("总分:88分") == 88
    assert BackendCodeReviewer.parse_score("未给出评分") == 0
