from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template


class ReviewPromptBuilder:
    def __init__(self, template_path: Path | None = None) -> None:
        self.template_path = template_path or Path(__file__).with_name("prompt_templates.yml")

    def build_messages(
        self,
        *,
        style: str,
        diffs_text: str,
        commits_text: str,
    ) -> list[dict[str, str]]:
        prompts = yaml.safe_load(self.template_path.read_text(encoding="utf-8"))[
            "code_review_prompt"
        ]
        system_prompt = Template(prompts["system_prompt"]).render(style=style)
        user_prompt_template = Template(prompts["user_prompt"]).render(style=style)
        user_prompt = user_prompt_template.format(
            diffs_text=diffs_text,
            commits_text=commits_text,
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
