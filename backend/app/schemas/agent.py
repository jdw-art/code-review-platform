from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentSessionCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    branch: str = Field(min_length=1, max_length=255)


class AgentSessionResponse(BaseModel):
    id: int
    project_id: int
    title: str
    status: str
    branch: str
    provider: str | None = None
    model: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None


class AgentMessageCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1)


class AgentMessageResponse(BaseModel):
    id: int
    session_id: int
    run_id: int | None = None
    role: str
    content: str
    status: str
    sequence: int
    content_format: str
    created_at: datetime


class AgentRunResponse(BaseModel):
    id: int
    session_id: int
    status: str
    stop_reason: str | None = None
    tool_steps: int
    attempts: int
    last_tool: str | None = None
    branch: str | None = None
    head_sha: str | None = None
    workspace_fingerprint: str | None = None
    runtime_identity_hash: str | None = None
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    completion_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentBranchOptionResponse(BaseModel):
    name: str
    is_default: bool = False


class AgentSSEEventResponse(BaseModel):
    event_type: str
    sequence: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
