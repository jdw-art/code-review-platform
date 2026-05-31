from __future__ import annotations

from datetime import datetime, timezone

from app.db.models import Project, ProjectTemplate, ReviewCommit, ReviewRecord


def _create_project(db_session) -> Project:
    template = ProjectTemplate(
        name="Python Review Template",
        code="python-review-template",
        description="Template for review records api tests",
        file_extensions=[".py"],
        review_prompt_template="review python changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Review API Project",
        key="review-api-project",
        platform_type="gitlab",
        repo_url="https://example.com/review-api-project.git",
        default_branch="main",
        review_enabled=True,
        template=template,
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)
    return project


def test_review_records_api_supports_mock_ingest_list_detail_and_raw(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)
    ingest_response = authenticated_superuser_client.post(
        "/api/v1/review-records/mock-ingest",
        json={
            "event_type": "merge_request",
            "project_key": project.key,
            "payload": {
                "project_name": "stale-name",
                "author": "alice",
                "title": "feat: add review api",
                "source_branch": "feature/review-api",
                "target_branch": "main",
                "score": 91.5,
                "review_result": "overall good",
                "summary": "2 issues found",
                "url": "https://example.com/mr/1",
                "url_slug": "mr-1",
                "additions": 18,
                "deletions": 5,
                "last_commit_id": "abc123",
                "agent_trace": {"steps": ["parsed", "reviewed"]},
                "commits": [
                    {"id": "abc123", "message": "feat: add review api", "author": "alice"},
                    {"id": "abc124", "message": "test: add api tests", "author": "alice"},
                ],
                "webhook_data": {"object_kind": "merge_request"},
                "updated_at": 1710002222,
            },
        },
    )
    assert ingest_response.status_code == 201
    ingested = ingest_response.json()
    assert ingested["is_duplicate"] is False

    record = db_session.get(ReviewRecord, ingested["id"])
    assert record is not None
    record.delivery_status = "delivered"
    record.error_message = None
    record.retry_count = 2
    record.reviewed_at = datetime(2024, 3, 9, 12, 34, 56, tzinfo=timezone.utc)
    record.failed_at = None
    db_session.commit()

    list_response = authenticated_superuser_client.get(
        "/api/v1/review-records",
        params={
            "page": 1,
            "page_size": 20,
            "project_id": project.id,
            "event_type": "merge_request",
            "author": "alice",
        },
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    listed = next(item for item in list_body["items"] if item["id"] == record.id)
    assert listed["project_name_snapshot"] == "Review API Project"
    assert listed["author"] == "alice"
    assert listed["platform_type"] == "gitlab"
    assert listed["delivery_status"] == "delivered"
    assert listed["error_message"] is None
    assert listed["retry_count"] == 2
    assert listed["reviewed_at"] == "2024-03-09T12:34:56Z"
    assert listed["failed_at"] is None
    assert listed["score"] == 91.5
    assert listed["commit_count"] == 2

    detail_response = authenticated_superuser_client.get(
        f"/api/v1/review-records/{record.id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == record.id
    assert detail["project_name_snapshot"] == "Review API Project"
    assert detail["template_name_snapshot"] == "Python Review Template"
    assert detail["platform_type"] == "gitlab"
    assert detail["delivery_status"] == "delivered"
    assert detail["error_message"] is None
    assert detail["retry_count"] == 2
    assert detail["reviewed_at"] == "2024-03-09T12:34:56Z"
    assert detail["failed_at"] is None
    assert detail["commits"][0]["message"] == "feat: add review api"
    assert detail["commits"][1]["message"] == "test: add api tests"

    filters_response = authenticated_superuser_client.get("/api/v1/review-records/filters")
    assert filters_response.status_code == 200
    filters_body = filters_response.json()
    assert "merge_request" in filters_body["event_types"]
    assert any(item["value"] == "alice" for item in filters_body["authors"])

    raw_response = authenticated_superuser_client.get(
        f"/api/v1/review-records/{record.id}/raw"
    )
    assert raw_response.status_code == 200
    raw = raw_response.json()
    assert raw["id"] == record.id
    assert raw["webhook_data"] == {"object_kind": "merge_request"}
    assert raw["agent_trace"] == {"steps": ["parsed", "reviewed"]}
    assert raw["extra_data"]["updated_at"] == 1710002222


def test_review_records_api_deduplicates_repeated_mock_events(
    authenticated_superuser_client,
    db_session,
) -> None:
    project = _create_project(db_session)
    payload = {
        "event_type": "push",
        "project_id": project.id,
        "payload": {
            "author": "dedupe-user",
            "branch": "feature/dedupe",
            "url_slug": "push-dedupe",
            "last_commit_id": "push-commit-1",
            "commits": [{"id": "push-commit-1", "message": "feat: dedupe push"}],
            "updated_at": 1710004444,
        },
    }

    first_response = authenticated_superuser_client.post(
        "/api/v1/review-records/mock-ingest",
        json=payload,
    )
    second_response = authenticated_superuser_client.post(
        "/api/v1/review-records/mock-ingest",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]
    assert first_response.json()["is_duplicate"] is False
    assert second_response.json()["is_duplicate"] is True


def test_review_records_api_exposes_chinese_openapi(
    client,
    authenticated_superuser_client,
) -> None:
    del authenticated_superuser_client

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/review-records"]["get"]
    assert operation["summary"] == "获取审查记录列表"
    assert "分页返回项目审查记录" in operation["description"]
