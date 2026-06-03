from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentSessionCreateRequest(BaseModel):
    title: str = "仓库助手"


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    status: str
    workspace_fingerprint: str
    snapshot_id: int | None
    created_at: datetime
    updated_at: datetime


class AgentMessageCreateRequest(BaseModel):
    content: str


class AgentMessageAcceptedResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    run_id: int
    status: str


class AgentMessageResponse(BaseModel):
    id: int
    session_id: int
    run_id: int | None
    role: str
    content: str
    content_format: str
    status: str
    sequence: int
    metadata: dict[str, Any]
    created_at: datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    project_id: int
    status: str
    stop_reason: str
    tool_steps: int
    attempts: int
    last_tool: str
    final_answer: str | None
    snapshot_id: int | None
    workspace_fingerprint: str
    prompt_metadata: dict[str, Any]
    completion_metadata: dict[str, Any]
