from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRunEvent


class AgentEventRecorder:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        run_id: int,
        session_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> AgentRunEvent:
        last_event = self.session.scalar(
            select(AgentRunEvent)
            .where(AgentRunEvent.run_id == run_id)
            .order_by(AgentRunEvent.sequence.desc())
            .limit(1)
        )
        event = AgentRunEvent(
            run_id=run_id,
            session_id=session_id,
            event_type=event_type,
            sequence=1 if last_event is None else last_event.sequence + 1,
            payload=dict(payload),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_after(
        self,
        *,
        session_id: int,
        after_id: int | None = None,
    ) -> list[AgentRunEvent]:
        stmt = (
            select(AgentRunEvent)
            .where(AgentRunEvent.session_id == session_id)
            .order_by(AgentRunEvent.id.asc())
        )
        if after_id is not None:
            stmt = stmt.where(AgentRunEvent.id > after_id)
        return list(self.session.scalars(stmt).all())
