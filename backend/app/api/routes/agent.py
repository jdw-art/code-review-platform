from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.db.models import User
from app.schemas.agent import (
    AgentMessageCreateRequest,
    AgentMessageResponse,
    AgentSessionCreateRequest,
    AgentSessionResponse,
)
from app.security.deps import require_permission
from app.services.agent_session_service import AgentSessionService


router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


@router.get(
    "/sessions",
    response_model=list[AgentSessionResponse],
    summary="获取 Repo Agent 会话列表",
)
async def list_agent_sessions(
    project_id: int,
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> list[AgentSessionResponse]:
    del current_user
    return await service.list_sessions(project_id)


@router.post(
    "/sessions",
    response_model=AgentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Repo Agent 会话",
)
async def create_agent_session(
    project_id: int,
    payload: AgentSessionCreateRequest,
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> AgentSessionResponse:
    return await service.create_session(current_user, project_id, payload)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=AgentMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Repo Agent 消息",
)
async def create_agent_message(
    project_id: int,
    session_id: int,
    payload: AgentMessageCreateRequest,
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> AgentMessageResponse:
    return await service.create_message(current_user, project_id, session_id, payload)


@router.get(
    "/sessions/{session_id}/stream",
    summary="订阅 Repo Agent SSE 事件流",
)
async def stream_agent_session(
    project_id: int,
    session_id: int,
    after_message_id: int = Query(default=0, ge=0),
    after_event_id: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> StreamingResponse:
    del current_user
    return StreamingResponse(
        service.stream_events(
            project_id,
            session_id,
            after_message_id=after_message_id,
            after_event_id=after_event_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
