from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_TOTAL_BUDGET = 12000
DEFAULT_SECTION_BUDGETS = {
    "prefix": 3600,
    "memory": 1600,
    "relevant_memory": 1200,
    "history": 5200,
}


def _tail_clip(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return "..." + text[-(limit - 3):]


@dataclass
class SectionRender:
    raw: str
    budget: int
    rendered: str


class ContextManager:
    def __init__(
        self,
        *,
        workspace_text: str,
        memory_state: dict[str, Any],
        history: list[dict[str, Any]],
        total_budget: int = DEFAULT_TOTAL_BUDGET,
        section_budgets: dict[str, int] | None = None,
    ) -> None:
        self.workspace_text = str(workspace_text)
        self.memory_state = dict(memory_state)
        self.history = list(history)
        self.total_budget = int(total_budget)
        self.section_budgets = dict(DEFAULT_SECTION_BUDGETS)
        if section_budgets:
            self.section_budgets.update({key: int(value) for key, value in section_budgets.items()})

    def build(self, user_message: str) -> tuple[str, dict[str, Any]]:
        memory_text = self._render_memory_text()
        relevant_memory_text = self._render_relevant_memory_text()
        history_text = self._render_history_text()
        current_request = f"Current user request:\n{user_message}"

        rendered = {
            "prefix": self._render_section("prefix", self.workspace_text),
            "memory": self._render_section("memory", memory_text),
            "relevant_memory": self._render_section("relevant_memory", relevant_memory_text),
            "history": self._render_section("history", history_text),
            "current_request": SectionRender(
                raw=current_request,
                budget=0,
                rendered=current_request,
            ),
        }

        prompt = self._assemble_prompt(rendered)
        metadata = {
            "prompt_chars": len(prompt),
            "sections": {
                name: {
                    "raw_chars": len(section.raw),
                    "rendered_chars": len(section.rendered),
                    "budget": section.budget,
                }
                for name, section in rendered.items()
            },
        }
        return prompt, metadata

    def _render_section(self, name: str, raw: str) -> SectionRender:
        budget = int(self.section_budgets.get(name, self.total_budget))
        return SectionRender(
            raw=raw,
            budget=budget,
            rendered=_tail_clip(raw, budget),
        )

    def _render_memory_text(self) -> str:
        working = self.memory_state.get("working", {})
        task_summary = working.get("task_summary", "")
        recent_files = working.get("recent_files", [])
        episodic_notes = self.memory_state.get("episodic_notes", [])
        file_summaries = self.memory_state.get("file_summaries", {})
        file_lines = "\n".join(f"- {path}" for path in recent_files) or "- none"
        note_lines = "\n".join(f"- {note}" for note in episodic_notes) or "- none"
        summary_lines = "\n".join(
            f"- {path}: {summary}"
            for path, summary in file_summaries.items()
        ) or "- none"
        return (
            "Memory:\n"
            f"- task_summary: {task_summary}\n"
            "- recent_files:\n"
            f"{file_lines}\n"
            "- episodic_notes:\n"
            f"{note_lines}\n"
            "- file_summaries:\n"
            f"{summary_lines}"
        )

    def _render_relevant_memory_text(self) -> str:
        note_candidates = self.memory_state.get("notes", [])
        lines = ["Relevant memory:"]
        if not note_candidates:
            lines.append("- none")
            return "\n".join(lines)
        for item in note_candidates:
            lines.append(f"- {item}")
        return "\n".join(lines)

    def _render_history_text(self) -> str:
        lines = ["History:"]
        if not self.history:
            lines.append("- none")
            return "\n".join(lines)
        for item in self.history:
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))
            lines.append(f"- {role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _assemble_prompt(rendered: dict[str, SectionRender]) -> str:
        return "\n\n".join(
            [
                rendered["prefix"].rendered,
                rendered["memory"].rendered,
                rendered["relevant_memory"].rendered,
                rendered["history"].rendered,
                rendered["current_request"].rendered,
            ]
        )
