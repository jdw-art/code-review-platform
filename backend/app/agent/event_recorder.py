from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


PersistEventCallback = Callable[[dict[str, Any]], None]


class EventRecorder:
    def __init__(
        self,
        *,
        persist_event: PersistEventCallback | None = None,
    ) -> None:
        self._persist_event = persist_event
        self._events: list[dict[str, Any]] = []
        self._sequence = 0

    def record(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        event = {
            "sequence": self._sequence,
            "event_type": str(event_type),
            "payload": deepcopy(payload or {}),
            "created_at": datetime.now(UTC),
        }
        self._events.append(event)
        if self._persist_event is not None:
            self._persist_event(deepcopy(event))
        return deepcopy(event)

    def export(self) -> list[dict[str, Any]]:
        return [deepcopy(event) for event in self._events]
