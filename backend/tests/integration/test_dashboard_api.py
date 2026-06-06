from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models import LlmModel, Project, ReviewRecord


def test_dashboard_overview_aggregates_review_scores(
    authenticated_superuser_client,
    db_session,
) -> None:
    first_project = Project(
        name="Payments API",
        key="payments-api",
        platform_type="gitlab",
        default_branch="main",
        is_active=True,
        review_enabled=True,
    )
    second_project = Project(
        name="Console Web",
        key="console-web",
        platform_type="github",
        default_branch="main",
        is_active=True,
        review_enabled=True,
    )
    third_project = Project(
        name="Async Worker",
        key="async-worker",
        platform_type="github",
        default_branch="main",
        is_active=False,
        review_enabled=True,
    )
    db_session.add_all([first_project, second_project, third_project])
    db_session.commit()
    db_session.refresh(first_project)
    db_session.refresh(second_project)
    db_session.refresh(third_project)

    db_session.add_all(
        [
            LlmModel(
                name="Gemini 2.5 Pro",
                provider="google",
                model_code="gemini-2.5-pro",
                temperature=0.2,
                is_default=True,
                is_active=True,
            ),
            LlmModel(
                name="Claude 3.7 Sonnet",
                provider="anthropic",
                model_code="claude-3-7-sonnet",
                temperature=0.1,
                is_default=False,
                is_active=True,
            ),
            LlmModel(
                name="GPT-4.1",
                provider="openai",
                model_code="gpt-4.1",
                temperature=0.3,
                is_default=False,
                is_active=False,
            ),
        ]
    )
    db_session.flush()

    now = datetime(2026, 6, 5, 9, 30, tzinfo=UTC)

    db_session.add_all(
        [
            ReviewRecord(
                project_id=first_project.id,
                event_type="merge_request",
                platform_type="gitlab",
                project_name_snapshot=first_project.name,
                author="alice",
                commit_count=1,
                commit_messages=["feat: tighten auth"],
                title="Add permission guardrails",
                branch="main",
                last_commit_id="abc1234def5678",
                score=95,
                review_status="reviewed",
                summary="Tightened auth checks and removed dead paths.",
                additions=180,
                deletions=42,
                created_at=now - timedelta(minutes=50),
                updated_at=now - timedelta(minutes=50),
            ),
            ReviewRecord(
                project_id=first_project.id,
                event_type="push",
                platform_type="gitlab",
                project_name_snapshot=first_project.name,
                author="alice",
                commit_count=1,
                commit_messages=["refactor: split dashboard serializer"],
                title="Refactor dashboard serializer",
                branch="release/metrics",
                last_commit_id="bcd2345efg6789",
                score=85,
                review_status="reviewed",
                summary="Split serializers to isolate transport contracts.",
                additions=95,
                deletions=20,
                created_at=now - timedelta(minutes=40),
                updated_at=now - timedelta(minutes=40),
            ),
            ReviewRecord(
                project_id=second_project.id,
                event_type="push",
                platform_type="github",
                project_name_snapshot=second_project.name,
                author="bob",
                commit_count=1,
                commit_messages=["feat: ship review filters"],
                title="Ship review filters",
                branch="feature/filters",
                last_commit_id="cde3456fgh7890",
                score=70,
                review_status="reviewed",
                summary="Introduced filter chips and query syncing.",
                additions=130,
                deletions=32,
                created_at=now - timedelta(minutes=30),
                updated_at=now - timedelta(minutes=30),
            ),
            ReviewRecord(
                project_id=second_project.id,
                event_type="pull_request",
                platform_type="github",
                project_name_snapshot=second_project.name,
                author="carol",
                commit_count=1,
                commit_messages=["fix: recover audit timeline"],
                title="Recover audit timeline",
                branch="hotfix/audit",
                last_commit_id="def4567ghi8901",
                score=None,
                review_status="failed",
                summary="Audit export failed because the history window regressed.",
                additions=40,
                deletions=18,
                created_at=now - timedelta(minutes=20),
                updated_at=now - timedelta(minutes=20),
            ),
            ReviewRecord(
                project_id=third_project.id,
                event_type="push",
                platform_type="github",
                project_name_snapshot=third_project.name,
                author="diana",
                commit_count=1,
                commit_messages=["chore: harden worker retries"],
                title="Harden worker retries",
                branch="chore/retries",
                last_commit_id="efg5678hij9012",
                score=88,
                review_status="reviewed",
                summary="Worker retry loop now backs off and preserves context.",
                additions=210,
                deletions=75,
                created_at=now - timedelta(minutes=10),
                updated_at=now - timedelta(minutes=10),
            ),
        ]
    )
    db_session.commit()

    response = authenticated_superuser_client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["total_projects"] == 3
    assert body["active_projects"] == 2
    assert body["total_review_records"] == 5
    assert body["average_score"] == 84.5
    assert body["active_model_name"] == "Gemini 2.5 Pro"
    assert [item["name"] for item in body["models"]] == [
        "Gemini 2.5 Pro",
        "Claude 3.7 Sonnet",
        "GPT-4.1",
    ]

    assert len(body["recent_reviews"]) == 4
    assert body["recent_reviews"][0] == {
        "id": body["recent_reviews"][0]["id"],
        "project_name": "Async Worker",
        "title": "Harden worker retries",
        "branch": "chore/retries",
        "commit_hash": "efg5678hij9012",
        "committer": "diana",
        "score": 88.0,
        "review_status": "reviewed",
        "summary": "Worker retry loop now backs off and preserves context.",
        "created_at": "2026-06-05T09:20:00Z",
    }
    assert body["recent_reviews"][-1]["project_name"] == "Payments API"

    assert body["project_chart"] == [
        {
            "name": "Payments API",
            "commits": 2,
            "avg_score": 90.0,
            "additions": 275,
            "deletions": 62,
        },
        {
            "name": "Console Web",
            "commits": 2,
            "avg_score": 70.0,
            "additions": 170,
            "deletions": 50,
        },
        {
            "name": "Async Worker",
            "commits": 1,
            "avg_score": 88.0,
            "additions": 210,
            "deletions": 75,
        },
    ]
    assert body["member_chart"] == [
        {
            "name": "alice",
            "commits": 2,
            "avg_score": 90.0,
            "additions": 275,
            "deletions": 62,
        },
        {
            "name": "diana",
            "commits": 1,
            "avg_score": 88.0,
            "additions": 210,
            "deletions": 75,
        },
        {
            "name": "bob",
            "commits": 1,
            "avg_score": 70.0,
            "additions": 130,
            "deletions": 32,
        },
        {
            "name": "carol",
            "commits": 1,
            "avg_score": 0.0,
            "additions": 40,
            "deletions": 18,
        },
    ]
    assert body["repo_health"] == [
        {
            "project_id": first_project.id,
            "name": "Payments API",
            "is_active": True,
            "review_count": 2,
            "average_score": 90.0,
            "last_review_at": "2026-06-05T08:50:00Z",
        },
        {
            "project_id": third_project.id,
            "name": "Async Worker",
            "is_active": False,
            "review_count": 1,
            "average_score": 88.0,
            "last_review_at": "2026-06-05T09:20:00Z",
        },
        {
            "project_id": second_project.id,
            "name": "Console Web",
            "is_active": True,
            "review_count": 2,
            "average_score": 70.0,
            "last_review_at": "2026-06-05T09:10:00Z",
        },
    ]


def test_dashboard_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
) -> None:
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/dashboard/overview"]["get"]
    assert operation["summary"] == "获取仪表盘概览"
    assert "返回高保真控制台所需的概览统计" in operation["description"]
