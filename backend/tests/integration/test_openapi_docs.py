from __future__ import annotations

import re


CHINESE_TEXT_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def test_all_business_api_operations_expose_chinese_openapi_descriptions(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    expected_operations = {
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/refresh", "post"),
        ("/api/v1/auth/logout", "post"),
        ("/api/v1/auth/logout-all", "post"),
        ("/api/v1/auth/change-password", "post"),
        ("/api/v1/me/access-context", "get"),
        ("/api/v1/me/profile", "get"),
        ("/api/v1/dashboard/overview", "get"),
        ("/api/v1/projects", "get"),
        ("/api/v1/projects", "post"),
        ("/api/v1/projects/options", "get"),
        ("/api/v1/projects/{project_id}", "get"),
        ("/api/v1/projects/{project_id}", "put"),
        ("/api/v1/projects/{project_id}/status", "patch"),
        ("/api/v1/project-templates", "get"),
        ("/api/v1/project-templates", "post"),
        ("/api/v1/project-templates/options", "get"),
        ("/api/v1/project-templates/{template_id}", "get"),
        ("/api/v1/project-templates/{template_id}", "put"),
        ("/api/v1/project-templates/{template_id}/status", "patch"),
        ("/api/v1/models", "get"),
        ("/api/v1/models", "post"),
        ("/api/v1/models/{model_id}", "get"),
        ("/api/v1/models/{model_id}", "put"),
        ("/api/v1/models/{model_id}/status", "patch"),
        ("/api/v1/notification-bots", "get"),
        ("/api/v1/notification-bots", "post"),
        ("/api/v1/notification-bots/{bot_id}", "get"),
        ("/api/v1/notification-bots/{bot_id}", "put"),
        ("/api/v1/notification-bots/{bot_id}/status", "patch"),
        ("/api/v1/review-records", "get"),
        ("/api/v1/review-records/filters", "get"),
        ("/api/v1/review-records/mock-ingest", "post"),
        ("/api/v1/review-records/{review_record_id}", "get"),
        ("/api/v1/review-records/{review_record_id}/raw", "get"),
        ("/api/v1/member-analytics", "get"),
        ("/api/v1/member-analytics/{project_member_id}", "get"),
        ("/api/v1/audit-logs", "get"),
        ("/api/v1/audit-logs/{log_id}", "get"),
        ("/api/v1/users", "get"),
        ("/api/v1/users", "post"),
        ("/api/v1/users/{user_id}", "get"),
        ("/api/v1/users/{user_id}", "patch"),
        ("/api/v1/users/{user_id}/status", "patch"),
        ("/api/v1/users/{user_id}/reset-password", "post"),
        ("/api/v1/users/{user_id}/roles", "put"),
        ("/api/v1/roles", "get"),
        ("/api/v1/roles", "post"),
        ("/api/v1/roles/{role_id}", "get"),
        ("/api/v1/roles/{role_id}", "patch"),
        ("/api/v1/roles/{role_id}", "delete"),
        ("/api/v1/roles/{role_id}/permissions", "put"),
        ("/api/v1/roles/{role_id}/menus", "put"),
        ("/api/v1/permissions", "get"),
        ("/api/v1/permissions", "post"),
        ("/api/v1/permissions/{permission_id}", "patch"),
        ("/api/v1/permissions/{permission_id}", "delete"),
        ("/api/v1/menus", "get"),
        ("/api/v1/menus/tree", "get"),
        ("/api/v1/menus", "post"),
        ("/api/v1/menus/{menu_id}", "patch"),
        ("/api/v1/menus/{menu_id}", "delete"),
    }

    for path, method in expected_operations:
        operation = schema["paths"][path][method]
        summary = operation.get("summary", "")
        description = operation.get("description", "")

        assert summary, f"{method.upper()} {path} is missing summary"
        assert description, f"{method.upper()} {path} is missing description"
        assert CHINESE_TEXT_PATTERN.search(summary), (
            f"{method.upper()} {path} summary should contain Chinese text"
        )
        assert CHINESE_TEXT_PATTERN.search(description), (
            f"{method.upper()} {path} description should contain Chinese text"
        )
