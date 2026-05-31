from __future__ import annotations

from app.review.reviewer.prompt_builder import ReviewPromptBuilder


def test_prompt_builder_renders_style_diffs_and_commits() -> None:
    builder = ReviewPromptBuilder()

    messages = builder.build_messages(
        style="gentle",
        diffs_text="diff --git a.py b.py",
        commits_text="feat: add login",
    )

    assert messages[0]["role"] == "system"
    assert "gentle" in messages[0]["content"]
    assert '多用"建议"、"可以考虑"等温和措辞' in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "diff --git a.py b.py" in messages[1]["content"]
    assert "feat: add login" in messages[1]["content"]
