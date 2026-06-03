from __future__ import annotations

from app.db.models import Project


def _create_project(db_session) -> Project:
    project = Project(
        name="Agent SSE Project",
        key="agent-sse-project",
        platform_type="github",
        repo_url="https://example.com/agent-sse.git",
        default_branch="main",
        description="Project for agent SSE tests",
        review_enabled=True,
        settings={},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_agent_sse_replays_existing_events(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)

    session_response = authenticated_superuser_client.post(
        f"/api/v1/projects/{project.id}/agent/sessions",
        json={"title": "SSE Session"},
    )
    session_id = session_response.json()["id"]

    message_response = authenticated_superuser_client.post(
        f"/api/v1/agent/sessions/{session_id}/messages",
        json={"content": "给我一个总结。"},
    )
    assert message_response.status_code == 201

    response = authenticated_superuser_client.get(
        f"/api/v1/agent/sessions/{session_id}/stream",
        params={"since_event_id": 0},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: run_started" in response.text
    assert "event: assistant_message" in response.text
    assert "event: final" in response.text
    assert "data:" in response.text
