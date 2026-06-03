from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.event_recorder import AgentEventRecorder
from app.agent.repository_provider import RepositoryContentProvider
from app.agent.run_service import AgentModelClient, AgentRunService
from app.agent.snapshot_service import RepositorySnapshotService
from app.agent.tool_gateway import AgentToolGateway
from app.db.models import AgentMessage, AgentRun, AgentSession, Project, User
from app.db.session import get_db
from app.schemas.agent import (
    AgentMessageAcceptedResponse,
    AgentMessageCreateRequest,
    AgentMessageResponse,
    AgentRunResponse,
    AgentSessionCreateRequest,
    AgentSessionResponse,
)
from app.schemas.common import DomainForbiddenError, DomainUnauthorizedError
from app.security.deps import PASSWORD_CHANGE_ALLOWED_PATHS, require_permission
from app.security.tokens import TokenError, decode_token
from app.services.access_context import AccessContextService
from app.services.agent_session_service import AgentSessionService


router = APIRouter(tags=["agent"])


class RepositoryProviderFactory(Protocol):
    def create(self, *, project: Project) -> RepositoryContentProvider:
        pass


class StaticRepositoryProvider:
    def __init__(self, project: Project) -> None:
        settings = dict(project.settings or {})
        self.project = project
        self.file_contents = dict(
            settings.get(
                "agent_file_contents",
                {
                    "README.md": f"# {project.name}\n\n{project.description or 'Repository assistant snapshot.'}",
                    "backend/app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                },
            )
        )
        self.file_tree = list(
            settings.get(
                "agent_file_tree",
                [{"path": path, "type": "file"} for path in self.file_contents.keys()],
            )
        )
        self.commit_records = list(
            settings.get(
                "agent_recent_commits",
                [{"id": "seed-1", "message": "feat: seed agent snapshot"}],
            )
        )

    def get_head_sha(self, *, ref: str) -> str:
        return str(self.project.settings.get("agent_head_sha", f"{ref}-head"))

    def get_file_tree(self, *, ref: str) -> list[dict[str, Any]]:
        del ref
        return list(self.file_tree)

    def get_snapshot_overview(self, *, ref: str) -> dict[str, Any]:
        del ref
        return {
            "readme": str(self.file_contents.get("README.md", "")).strip(),
            "project_name": self.project.name,
        }

    def get_recent_commit_records(self, *, limit: int) -> list[dict[str, Any]]:
        return list(self.commit_records[:limit])

    def list_files(self, *, path: str, ref: str) -> str:
        del ref
        normalized = path.strip("/") or "."
        matches = []
        for item in self.file_tree:
            current = str(item.get("path", "")).strip("/")
            if normalized == "." or current == normalized or current.startswith(f"{normalized}/"):
                matches.append(current)
        return "\n".join(matches)

    def read_file(self, *, path: str, start: int, end: int, ref: str) -> str:
        del ref
        content = str(self.file_contents.get(path, f"{path} not found"))
        lines = content.splitlines()
        if start > len(lines):
            return ""
        return "\n".join(lines[start - 1 : end])

    def search(self, *, pattern: str, path: str, ref: str) -> str:
        del ref
        results: list[str] = []
        normalized = path.strip("/") or "."
        for file_path, content in self.file_contents.items():
            if normalized != "." and not file_path.startswith(normalized):
                continue
            for index, line in enumerate(content.splitlines(), start=1):
                if pattern.lower() in line.lower():
                    results.append(f"{file_path}:{index}:{line}")
        return "\n".join(results) or "no matches"

    def get_project_overview(self) -> str:
        return str(self.file_contents.get("README.md", "")).strip()

    def get_recent_commits(self, *, limit: int) -> str:
        records = self.get_recent_commit_records(limit=limit)
        return "\n".join(
            f"{item.get('id', '')} {item.get('message', '')}".strip()
            for item in records
        )


class DefaultRepositoryProviderFactory:
    def create(self, *, project: Project) -> RepositoryContentProvider:
        return StaticRepositoryProvider(project)


class EchoAgentModelClient:
    def complete(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        del prompt
        project_id = metadata.get("project_id")
        return f"已完成当前仓库问题的基础总结（project_id={project_id}）。"


def get_repository_provider_factory() -> RepositoryProviderFactory:
    return DefaultRepositoryProviderFactory()


def get_agent_model_client() -> AgentModelClient:
    return EchoAgentModelClient()


async def require_agent_stream_read_permission(
    request: Request,
    db: Session = Depends(get_db),
    access_context_service: AccessContextService = Depends(),
    access_token: str | None = Query(default=None),
) -> User:
    token = access_token
    if token is None:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip() or None
    if token is None:
        raise DomainUnauthorizedError(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication required.",
        )

    try:
        claims = decode_token(token, expected_token_type="access")
    except TokenError as exc:
        raise DomainUnauthorizedError(
            code="INVALID_ACCESS_TOKEN",
            message="Invalid or expired access token.",
        ) from exc
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DomainUnauthorizedError(
            code="INVALID_ACCESS_TOKEN",
            message="Invalid or expired access token.",
        ) from exc

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise DomainUnauthorizedError(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication required.",
        )
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_ALLOWED_PATHS:
        raise DomainForbiddenError(
            code="PASSWORD_CHANGE_REQUIRED",
            message="Password change required.",
        )
    permission_codes = await access_context_service.get_permission_codes(user.id)
    if not user.is_superuser and "project:read" not in permission_codes:
        raise DomainForbiddenError(
            code="FORBIDDEN",
            message="Forbidden.",
        )
    return user


@router.get(
    "/projects/{project_id}/agent/sessions",
    response_model=list[AgentSessionResponse],
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取仓库助手会话列表",
    description="返回指定项目的仓库助手会话列表。需要 `project:read` 权限。",
)
async def list_agent_sessions(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[AgentSessionResponse]:
    _get_project_or_404(db, project_id)
    service = AgentSessionService(db)
    return [AgentSessionResponse.model_validate(item) for item in service.list_sessions(project_id=project_id)]


@router.post(
    "/projects/{project_id}/agent/sessions",
    response_model=AgentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建仓库助手会话",
    description="为指定项目创建一条仓库理解助手会话。需要 `project:read` 权限。",
)
async def create_agent_session(
    project_id: int,
    payload: AgentSessionCreateRequest,
    current_user: User = Depends(require_permission("project:read")),
    db: Session = Depends(get_db),
    provider_factory: RepositoryProviderFactory = Depends(get_repository_provider_factory),
) -> AgentSessionResponse:
    project = _get_project_or_404(db, project_id)
    provider = provider_factory.create(project=project)
    snapshot = RepositorySnapshotService(db).ensure_ready_snapshot(project=project, provider=provider)
    service = AgentSessionService(db)
    agent_session = service.create_session(
        project=project,
        title=payload.title,
        created_by=current_user.id,
        snapshot=snapshot,
    )
    return AgentSessionResponse.model_validate(agent_session)


@router.get(
    "/agent/sessions/{session_id}",
    response_model=AgentSessionResponse,
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取仓库助手会话详情",
    description="返回单个仓库助手会话详情。需要 `project:read` 权限。",
)
async def get_agent_session(
    session_id: int,
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    agent_session = _get_session_or_404(db, session_id)
    return AgentSessionResponse.model_validate(agent_session)


@router.get(
    "/agent/sessions/{session_id}/messages",
    response_model=list[AgentMessageResponse],
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取仓库助手消息列表",
    description="返回单个仓库助手会话下的消息流。需要 `project:read` 权限。",
)
async def list_agent_messages(
    session_id: int,
    db: Session = Depends(get_db),
) -> list[AgentMessageResponse]:
    agent_session = _get_session_or_404(db, session_id)
    service = AgentSessionService(db)
    return [_to_message_response(item) for item in service.list_messages(session_id=agent_session.id)]


@router.post(
    "/agent/sessions/{session_id}/messages",
    response_model=AgentMessageAcceptedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发送仓库助手消息",
    description="创建用户消息、assistant 占位消息并同步执行一轮 agent run。需要 `project:read` 权限。",
)
async def create_agent_message(
    session_id: int,
    payload: AgentMessageCreateRequest,
    current_user: User = Depends(require_permission("project:read")),
    db: Session = Depends(get_db),
    provider_factory: RepositoryProviderFactory = Depends(get_repository_provider_factory),
    model_client: AgentModelClient = Depends(get_agent_model_client),
) -> AgentMessageAcceptedResponse:
    del current_user
    agent_session = _get_session_or_404(db, session_id)
    project = _get_project_or_404(db, agent_session.project_id)
    provider = provider_factory.create(project=project)
    snapshot = RepositorySnapshotService(db).ensure_ready_snapshot(project=project, provider=provider)
    agent_session.snapshot_id = snapshot.id
    db.commit()
    db.refresh(agent_session)

    session_service = AgentSessionService(db)
    user_message, assistant_message, run = session_service.create_message_pair_and_run(
        session=agent_session,
        content=payload.content,
    )
    AgentRunService(
        session=db,
        model_client=model_client,
        tool_gateway=AgentToolGateway(provider=provider),
        event_recorder=AgentEventRecorder(db),
        session_service=session_service,
    ).run(run.id)
    return AgentMessageAcceptedResponse(
        session_id=agent_session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        run_id=run.id,
        status="accepted",
    )


@router.get(
    "/agent/sessions/{session_id}/stream",
    dependencies=[Depends(require_permission("project:read"))],
    summary="回放仓库助手事件流",
    description="以 SSE 格式回放指定会话的已有 run events，支持 `Last-Event-ID` 或 `since_event_id`。需要 `project:read` 权限。",
)
async def stream_agent_session(
    session_id: int,
    current_user: User = Depends(require_agent_stream_read_permission),
    db: Session = Depends(get_db),
    since_event_id: int | None = Query(default=None),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    del current_user
    agent_session = _get_session_or_404(db, session_id)
    after_id = since_event_id
    if after_id is None and last_event_id:
        try:
            after_id = int(last_event_id)
        except ValueError:
            after_id = None
    recorder = AgentEventRecorder(db)
    events = recorder.list_after(
        session_id=agent_session.id,
        after_id=None if after_id in (None, 0) else after_id,
    )
    return StreamingResponse(
        _iter_sse(events),
        media_type="text/event-stream",
    )


@router.post(
    "/agent/sessions/{session_id}/snapshot/refresh",
    response_model=AgentSessionResponse,
    summary="刷新仓库助手快照",
    description="为当前会话所属项目刷新最新仓库快照。需要 `project:update` 权限。",
)
async def refresh_agent_snapshot(
    session_id: int,
    current_user: User = Depends(require_permission("project:update")),
    db: Session = Depends(get_db),
    provider_factory: RepositoryProviderFactory = Depends(get_repository_provider_factory),
) -> AgentSessionResponse:
    del current_user
    agent_session = _get_session_or_404(db, session_id)
    project = _get_project_or_404(db, agent_session.project_id)
    provider = provider_factory.create(project=project)
    snapshot = RepositorySnapshotService(db).ensure_ready_snapshot(project=project, provider=provider)
    agent_session.snapshot_id = snapshot.id
    db.commit()
    db.refresh(agent_session)
    return AgentSessionResponse.model_validate(agent_session)


@router.get(
    "/agent/runs/{run_id}",
    response_model=AgentRunResponse,
    dependencies=[Depends(require_permission("project:read"))],
    summary="获取仓库助手运行详情",
    description="返回单个仓库助手 run 的状态与元数据。需要 `project:read` 权限。",
)
async def get_agent_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    run = _get_run_or_404(db, run_id)
    return AgentRunResponse.model_validate(run)


def _iter_sse(events: list[Any]) -> Iterator[str]:
    for event in events:
        payload = {
            "id": event.id,
            "run_id": event.run_id,
            "session_id": event.session_id,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "payload": event.payload,
        }
        yield f"id: {event.id}\n"
        yield f"event: {event.event_type}\n"
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在。")
    return project


def _get_session_or_404(db: Session, session_id: int) -> AgentSession:
    agent_session = db.get(AgentSession, session_id)
    if agent_session is None:
        raise HTTPException(status_code=404, detail="会话不存在。")
    return agent_session


def _get_run_or_404(db: Session, run_id: int) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="运行不存在。")
    return run


def _to_message_response(message: AgentMessage) -> AgentMessageResponse:
    return AgentMessageResponse(
        id=message.id,
        session_id=message.session_id,
        run_id=message.run_id,
        role=message.role,
        content=message.content,
        content_format=message.content_format,
        status=message.status,
        sequence=message.sequence,
        metadata=dict(message.metadata_json or {}),
        created_at=message.created_at,
    )
