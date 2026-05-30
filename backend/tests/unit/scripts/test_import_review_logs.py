from __future__ import annotations

from scripts.import_review_logs import (
    build_import_jobs,
    build_mock_ingest_request,
)


def test_build_import_jobs_skips_repo_records_and_unresolved_projects() -> None:
    project_key_by_name = {
        "ai-code-reviewer": "ai-code-reviewer",
        "agentic-rag": "agentic-rag",
    }
    merge_request_records = [
        {
            "id": 1,
            "project_name": "ai-code-reviewer",
            "author": "jdw-art",
            "source_branch": "feature/demo",
            "target_branch": "main",
            "updated_at": 1779729656,
            "commit_messages": "docs: test",
            "score": 80,
            "review_result": "ok",
            "url": "https://github.com/jdw-art/ai-code-reviewer/pull/1",
            "additions": 1,
            "deletions": 0,
            "last_commit_id": "abc123",
        },
        {
            "id": 2,
            "project_name": "repo",
            "author": "octocat",
            "source_branch": "feature/demo",
            "target_branch": "main",
            "updated_at": 1779729657,
            "commit_messages": "docs: skip",
            "score": 70,
            "review_result": "skip",
            "url": "https://github.com/owner/repo/pull/1",
            "additions": 1,
            "deletions": 1,
            "last_commit_id": "skip123",
        },
        {
            "id": 3,
            "project_name": "missing-project",
            "author": "alice",
            "source_branch": "feature/demo",
            "target_branch": "main",
            "updated_at": 1779729658,
            "commit_messages": "docs: missing",
            "score": 60,
            "review_result": "missing",
            "url": "https://github.com/example/missing/pull/1",
            "additions": 1,
            "deletions": 1,
            "last_commit_id": "missing123",
        },
    ]
    push_records = [
        {
            "id": 4,
            "project_name": "agentic-rag",
            "author": "jdw-art",
            "branch": "feat/test",
            "updated_at": 1779729660,
            "commit_messages": "feat: add import script",
            "score": 92,
            "review_result": "looks good",
            "additions": 5,
            "deletions": 2,
        }
    ]

    jobs = build_import_jobs(
        merge_request_records=merge_request_records,
        push_records=push_records,
        project_key_by_name=project_key_by_name,
        skipped_project_names={"repo"},
    )

    assert len(jobs.requests) == 2
    assert [job.payload["payload"]["external_event_id"] for job in jobs.requests] == [
        "mr:1",
        "push:4",
    ]
    assert jobs.skipped_records == [
        {"event_type": "merge_request", "source_id": 2, "project_name": "repo", "reason": "skipped_project_name"},
        {"event_type": "merge_request", "source_id": 3, "project_name": "missing-project", "reason": "project_not_found"},
    ]


def test_build_mock_ingest_request_maps_merge_request_fields() -> None:
    request_payload = build_mock_ingest_request(
        event_type="merge_request",
        project_key="ai-code-reviewer",
        source_record={
            "id": 6,
            "project_name": "ai-code-reviewer",
            "project_id": "jdw-art/ai-code-reviewer",
            "author": "jdw-art",
            "source_branch": "feature/20250526-multi-agent",
            "target_branch": "main",
            "updated_at": 1779890625,
            "commit_messages": "feat: one; fix: two",
            "score": 56,
            "review_result": "review body",
            "url": "https://github.com/jdw-art/ai-code-reviewer/pull/2",
            "additions": 10,
            "deletions": 4,
            "last_commit_id": "def456",
            "agent_trace": "",
            "platform": "github",
            "review_mode": "deep",
            "review_profile": "strict",
            "risk_level": "high",
        },
        source_label="historical_json_import",
    )

    assert request_payload["event_type"] == "merge_request"
    assert request_payload["project_key"] == "ai-code-reviewer"
    assert request_payload["source"] == "historical_json_import"
    assert request_payload["payload"]["external_event_id"] == "mr:6"
    assert request_payload["payload"]["url_slug"] == "jdw-art/ai-code-reviewer/pull/2"
    assert request_payload["payload"]["source_project_id"] == "jdw-art/ai-code-reviewer"
    assert request_payload["payload"]["agent_trace"] == {}
    assert request_payload["payload"]["commits"] == [
        {
            "id": "mr:6:1",
            "author": "jdw-art",
            "message": "feat: one",
            "timestamp": 1779890625,
        },
        {
            "id": "def456",
            "author": "jdw-art",
            "message": "fix: two",
            "timestamp": 1779890625,
        },
    ]


def test_build_mock_ingest_request_maps_push_fields() -> None:
    request_payload = build_mock_ingest_request(
        event_type="push",
        project_key="agentic-rag",
        source_record={
            "id": 4,
            "project_name": "agentic-rag",
            "author": "jdw-art",
            "branch": "feat/document-identity-v2",
            "updated_at": 1779726840,
            "commit_messages": "feat: simulate webhook review",
            "score": 92,
            "review_result": "### 模拟 Review",
            "additions": 1,
            "deletions": 1,
        },
        source_label="historical_json_import",
    )

    assert request_payload["event_type"] == "push"
    assert request_payload["project_key"] == "agentic-rag"
    assert request_payload["payload"]["external_event_id"] == "push:4"
    assert request_payload["payload"]["branch"] == "feat/document-identity-v2"
    assert request_payload["payload"]["commits"] == [
        {
            "id": "push:4:1",
            "author": "jdw-art",
            "message": "feat: simulate webhook review",
            "timestamp": 1779726840,
        }
    ]
