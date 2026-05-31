from __future__ import annotations

import app.review.reporting.daily_report_renderer as renderer_module
from app.review.llm.provider import ReviewerLLMConfig
from app.review.reporting.daily_report_renderer import DailyReportRenderer


class FakeClient:
    def __init__(self, response_text: str = "## 日报") -> None:
        self.response_text = response_text
        self.messages: list[list[dict[str, str]]] = []

    def completions(self, *, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        return self.response_text


def test_daily_report_renderer_serializes_rows_and_calls_client(monkeypatch) -> None:
    built_configs: list[ReviewerLLMConfig] = []
    client = FakeClient(response_text="## 代码提交日报")

    monkeypatch.setattr(
        renderer_module,
        "load_reviewer_llm_config",
        lambda: ReviewerLLMConfig(
            provider="openai",
            api_key="openai-key",
            api_base_url="https://example.com/v1",
            model="gpt-4o-mini",
        ),
    )

    def fake_build_llm_client(config: ReviewerLLMConfig) -> FakeClient:
        built_configs.append(config)
        return client

    monkeypatch.setattr(renderer_module, "build_llm_client", fake_build_llm_client)

    renderer = DailyReportRenderer()
    report = renderer.generate_report(
        [
            {
                "author": "张三",
                "commit_messages": ["feat: add login"],
                "review_result": "总分:90分",
                "score": 90,
                "project_name": "Portal",
                "updated_at": 1710000000,
            }
        ]
    )

    assert report == "## 代码提交日报"
    assert built_configs == [
        ReviewerLLMConfig(
            provider="openai",
            api_key="openai-key",
            api_base_url="https://example.com/v1",
            model="gpt-4o-mini",
        )
    ]
    assert client.messages == [
        [
            {
                "role": "user",
                "content": (
                    "下面是以json格式记录员工代码提交信息。请总结这些信息，生成每个员工的工作日报摘要。"
                    "员工姓名直接用json内容中的author属性值，不要进行转换。特别要求:以Markdown格式返回。\n"
                    '[{"author": "张三", "commit_messages": ["feat: add login"], '
                    '"review_result": "总分:90分", "score": 90, "project_name": "Portal", '
                    '"updated_at": 1710000000}]'
                ),
            }
        ]
    ]
