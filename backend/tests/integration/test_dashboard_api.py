from __future__ import annotations

from app.db.models import Project, ReviewRecord


def test_dashboard_overview_aggregates_review_scores(
    authenticated_superuser_client,
    db_session,
) -> None:
    active_project = Project(
        name="Dashboard Active Project",
        key="dashboard-active",
        platform_type="gitlab",
        default_branch="main",
        is_active=True,
        review_enabled=True,
    )
    inactive_project = Project(
        name="Dashboard Inactive Project",
        key="dashboard-inactive",
        platform_type="github",
        default_branch="main",
        is_active=False,
        review_enabled=True,
    )
    db_session.add_all([active_project, inactive_project])
    db_session.commit()
    db_session.refresh(active_project)
    db_session.refresh(inactive_project)

    db_session.add_all(
        [
            ReviewRecord(
                project_id=active_project.id,
                event_type="merge_request",
                platform_type="gitlab",
                project_name_snapshot=active_project.name,
                author="alice",
                commit_count=1,
                commit_messages=["feat: add metrics"],
                score=80,
                review_status="reviewed",
            ),
            ReviewRecord(
                project_id=active_project.id,
                event_type="push",
                platform_type="gitlab",
                project_name_snapshot=active_project.name,
                author="bob",
                commit_count=1,
                commit_messages=["fix: refine metrics"],
                score=60,
                review_status="reviewed",
            ),
            ReviewRecord(
                project_id=inactive_project.id,
                event_type="push",
                platform_type="github",
                project_name_snapshot=inactive_project.name,
                author="carol",
                commit_count=1,
                commit_messages=["docs: add dashboard notes"],
                score=None,
                review_status="failed",
            ),
        ]
    )
    db_session.commit()

    response = authenticated_superuser_client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["total_projects"] == 2
    assert body["active_projects"] == 1
    assert body["total_review_records"] == 3
    assert body["average_score"] == 70.0


def test_dashboard_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
) -> None:
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/dashboard/overview"]["get"]
    assert operation["summary"] == "获取仪表盘概览"
    assert "返回项目、审查记录与评分概览统计" in operation["description"]
