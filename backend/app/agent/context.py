from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.memory import render_memory_text, select_relevant_memory


DEFAULT_TOTAL_BUDGET = 12_000
DEFAULT_SECTION_BUDGETS = {
    "prefix": 3_600,
    "memory": 1_600,
    "relevant_memory": 1_200,
    "history": 5_200,
}
DEFAULT_SECTION_FLOORS = {
    "prefix": 1_200,
    "memory": 400,
    "relevant_memory": 300,
    "history": 1_500,
}
DEFAULT_REDUCTION_ORDER = ("relevant_memory", "history", "memory", "prefix")
SECTION_ORDER = ("prefix", "memory", "relevant_memory", "history", "current_request")
CURRENT_REQUEST_SECTION = "current_request"


def _prefix_clip(text: str, limit: int) -> str:
    text = str(text)
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def _suffix_clip(text: str, limit: int) -> str:
    text = str(text)
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[-limit:]
    return "..." + text[-(limit - 3) :]


@dataclass(slots=True)
class SectionRender:
    raw: str
    budget: int | None
    rendered: str

    @property
    def raw_chars(self) -> int:
        return len(self.raw)

    @property
    def rendered_chars(self) -> int:
        return len(self.rendered)


class ContextManager:
    def __init__(
        self,
        *,
        total_budget: int = DEFAULT_TOTAL_BUDGET,
        section_budgets: dict[str, int] | None = None,
        section_floors: dict[str, int] | None = None,
        reduction_order: tuple[str, ...] | None = None,
    ) -> None:
        self.total_budget = int(total_budget)
        self.section_budgets = dict(DEFAULT_SECTION_BUDGETS)
        if section_budgets:
            self.section_budgets.update({str(key): int(value) for key, value in section_budgets.items()})
        self.section_floors = dict(DEFAULT_SECTION_FLOORS)
        if section_floors:
            self.section_floors.update({str(key): int(value) for key, value in section_floors.items()})
        self.reduction_order = tuple(reduction_order or DEFAULT_REDUCTION_ORDER)

    def build(
        self,
        *,
        prefix: str = "",
        memory: str | None = None,
        memory_state: dict[str, Any] | None = None,
        relevant_memory: str | list[str] | None = None,
        history: str = "",
        current_request: str,
    ) -> tuple[str, dict[str, Any]]:
        rendered_sections = {
            "prefix": str(prefix),
            "memory": self._resolve_memory_text(memory=memory, memory_state=memory_state),
            "relevant_memory": self._resolve_relevant_memory(
                relevant_memory=relevant_memory,
                memory_state=memory_state,
                query=current_request,
            ),
            "history": str(history),
            CURRENT_REQUEST_SECTION: str(current_request),
        }
        budgets = dict(self.section_budgets)
        rendered = self._render_sections(rendered_sections, budgets)
        prompt = self._assemble_prompt(rendered)
        reduction_log: list[dict[str, int | str]] = []

        while len(prompt) > self.total_budget:
            overflow = len(prompt) - self.total_budget
            reduced = False
            for section in self.reduction_order:
                floor = int(self.section_floors.get(section, 0))
                current_budget = int(budgets.get(section, 0))
                if current_budget <= floor:
                    continue
                new_budget = max(floor, current_budget - overflow)
                if new_budget >= current_budget:
                    continue
                reduction_log.append(
                    {
                        "section": section,
                        "before_chars": current_budget,
                        "after_chars": new_budget,
                        "overflow_chars": overflow,
                    }
                )
                budgets[section] = new_budget
                rendered = self._render_sections(rendered_sections, budgets)
                prompt = self._assemble_prompt(rendered)
                reduced = True
                break
            if not reduced:
                break

        metadata = {
            "prompt_chars": len(prompt),
            "prompt_budget_chars": self.total_budget,
            "prompt_over_budget": len(prompt) > self.total_budget,
            "prefix": rendered["prefix"].rendered,
            "memory": rendered["memory"].rendered,
            "relevant_memory": rendered["relevant_memory"].rendered,
            "history": rendered["history"].rendered,
            "current_request": rendered[CURRENT_REQUEST_SECTION].rendered,
            "section_order": list(SECTION_ORDER),
            "reduction_order": list(self.reduction_order),
            "section_budgets": {
                section: (None if section == CURRENT_REQUEST_SECTION else int(budgets.get(section, 0)))
                for section in SECTION_ORDER
            },
            "sections": {
                section: {
                    "raw_chars": rendered[section].raw_chars,
                    "budget_chars": rendered[section].budget,
                    "rendered_chars": rendered[section].rendered_chars,
                }
                for section in SECTION_ORDER
            },
            "raw_sections": {
                section: rendered[section].raw
                for section in SECTION_ORDER
            },
            "rendered_sections": {
                section: rendered[section].rendered
                for section in SECTION_ORDER
            },
            "budget_reductions": reduction_log,
        }
        return prompt, metadata

    def _resolve_memory_text(
        self,
        *,
        memory: str | None,
        memory_state: dict[str, Any] | None,
    ) -> str:
        if memory is not None:
            return str(memory)
        if memory_state is None:
            return "Memory:\n- task: -\n- recent_files: -\n- file_summaries: -\n- episodic_notes: 0"
        return render_memory_text(memory_state)

    def _resolve_relevant_memory(
        self,
        *,
        relevant_memory: str | list[str] | None,
        memory_state: dict[str, Any] | None,
        query: str,
    ) -> str:
        if isinstance(relevant_memory, str):
            return relevant_memory
        if isinstance(relevant_memory, list):
            notes = [str(item).strip() for item in relevant_memory if str(item).strip()]
        elif memory_state is not None:
            notes = [item["text"] for item in select_relevant_memory(memory_state, query)]
        else:
            notes = []
        if not notes:
            return "Relevant memory:\n- none"
        return "\n".join(["Relevant memory:", *[f"- {note}" for note in notes]])

    def _render_sections(
        self,
        section_texts: dict[str, str],
        budgets: dict[str, int],
    ) -> dict[str, SectionRender]:
        rendered: dict[str, SectionRender] = {}
        for section in SECTION_ORDER:
            raw = section_texts[section]
            if section == CURRENT_REQUEST_SECTION:
                rendered[section] = SectionRender(raw=raw, budget=None, rendered=raw)
                continue
            budget = int(budgets.get(section, 0))
            rendered[section] = SectionRender(
                raw=raw,
                budget=budget,
                rendered=self._clip_section(section=section, raw=raw, budget=budget),
            )
        return rendered

    def _clip_section(self, *, section: str, raw: str, budget: int) -> str:
        if section == "history":
            return _suffix_clip(raw, budget)
        return _prefix_clip(raw, budget)

    def _assemble_prompt(self, rendered: dict[str, SectionRender]) -> str:
        return "\n\n".join(rendered[section].rendered for section in SECTION_ORDER).strip()
