from __future__ import annotations

from app.db.models import Project, ProjectMember, ReviewRecord


def test_member_analytics_api_supports_list_and_detail(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = Project(
        name="Member Analytics Project",
        key="member-analytics-project",
        platform_type="gitlab",
        default_branch="main",
        is_active=True,
        review_enabled=True,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    project_member = ProjectMember(
        project_id=project.id,
        member_name="alice",
        member_email="alice@example.com",
        role_name="maintainer",
        is_active=True,
    )
    db_session.add(project_member)
    db_session.add_all(
        [
            ReviewRecord(
                project_id=project.id,
                event_type="merge_request",
                project_name_snapshot=project.name,
                author="alice",
                title="feat: add analytics api",
                commit_count=1,
                commit_messages=["feat: add analytics api"],
                score=92,
                review_status="completed",
                url_slug="mr-1",
                additions=14,
                deletions=3,
            ),
            ReviewRecord(
                project_id=project.id,
                event_type="push",
                project_name_snapshot=project.name,
                author="alice",
                title="fix: tighten analytics api",
                commit_count=1,
                commit_messages=["fix: tighten analytics api"],
                score=68,
                review_status="completed",
                url_slug="push-1",
                additions=6,
                deletions=2,
            ),
            ReviewRecord(
                project_id=project.id,
                event_type="push",
                project_name_snapshot=project.name,
                author="bob",
                title="docs: update member analytics",
                commit_count=1,
                commit_messages=["docs: update member analytics"],
                score=75,
                review_status="completed",
                url_slug="push-2",
                additions=2,
                deletions=1,
            ),
        ]
    )
    db_session.commit()

    list_response = authenticated_superuser_client.get(
        "/api/v1/member-analytics",
        params={"page": 1, "page_size": 20, "project_id": project.id},
    )

    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    alice = next(item for item in list_body["items"] if item["member_name"] == "alice")
    assert alice["project_member_id"] == project_member.id
    assert alice["project_id"] == project.id
    assert alice["review_count"] == 2
    assert alice["average_score"] == 80.0
    assert alice["total_additions"] == 20
    assert alice["total_deletions"] == 5

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/member-analytics/{project_member.id}",
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["project_member_id"] == project_member.id
    assert detail["member_name"] == "alice"
    assert detail["project_id"] == project.id
    assert detail["role_name"] == "maintainer"
    assert detail["review_count"] == 2
    assert {item["url_slug"] for item in detail["recent_reviews"]} == {"mr-1", "push-1"}


def test_member_analytics_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
) -> None:
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/member-analytics"]["get"]
    assert operation["summary"] == "获取成员分析列表"
    assert "分页返回项目成员的审查表现统计" in operation["description"]
