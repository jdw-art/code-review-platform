from __future__ import annotations

import json
from typing import Any

from app.review.llm.provider import load_reviewer_llm_config
from app.review.reviewer.backend_reviewer import build_llm_client


class DailyReportRenderer:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client or build_llm_client(load_reviewer_llm_config())

    def generate_report(self, rows: list[dict[str, object]]) -> str:
        data = json.dumps(rows, ensure_ascii=False)
        prompt = (
            "下面是以json格式记录员工代码提交信息。请总结这些信息，生成每个员工的工作日报摘要。"
            "员工姓名直接用json内容中的author属性值，不要进行转换。特别要求:以Markdown格式返回。\n"
            f"{data}"
        )
        return self.client.completions(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )
