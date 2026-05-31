from pathlib import Path

from app.db.models import Project, ProjectTemplate, ReviewRecord
from sqlalchemy import select

from scripts.verify_full_review_flow import (
    analyze_execution_result,
    build_branch_name,
    build_execution_plan,
    build_execution_result,
    build_run_id,
    check_github_comment_status,
    classify_result,
    collect_observation_snapshot,
    collect_runtime_observation,
    execute_plan,
    fetch_latest_review_records,
    fetch_redis_queue_head,
    fetch_redis_queue_length,
    find_matching_review_record,
    GitCommandResult,
    ObservationSnapshot,
    patch_readme,
    prepare_local_git_change,
    push_verification_branch,
    render_report,
    run_git_command,
    WorkerProcessManager,
    wait_for_review_outcome,
    run_preflight_checks,
    restore_readme,
    write_report,
)


def test_build_run_id_and_branch_name() -> None:
    run_id = build_run_id(prefix="verify/review-flow")
    branch_name = build_branch_name(prefix="verify/review-flow", run_id=run_id)

    assert run_id.startswith("verify-review-flow-")
    assert branch_name == f"verify/review-flow/{run_id}"


def test_preflight_reports_missing_required_env(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)

    result = run_preflight_checks(repo_root="/tmp/repo", backend_root="/tmp/backend")

    assert result.ok is False
    assert "GITHUB_ACCESS_TOKEN" in result.errors


def test_worker_manager_tracks_process_lifecycle() -> None:
    manager = WorkerProcessManager(command=["python", "-m", "app.workers.review_worker"])

    assert manager.is_configured() is True


def test_worker_manager_can_start_and_stop(tmp_path) -> None:
    manager = WorkerProcessManager(
        command=["python", "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
    )

    process = manager.start()
    assert process.poll() is None

    manager.stop()
    assert process.poll() is not None


def test_worker_manager_captures_output_after_stop(tmp_path) -> None:
    manager = WorkerProcessManager(
        command=[
            "python",
            "-c",
            "import sys; print('worker ok'); print('worker err', file=sys.stderr)",
        ],
        cwd=tmp_path,
    )

    process = manager.start()
    process.wait(timeout=5)
    manager.stop()

    assert "worker ok" in manager.stdout
    assert "worker err" in manager.stderr


def test_classify_result_distinguishes_core_and_full_pass() -> None:
    assert classify_result(core_pass=True, comment_pass=False) == "核心通过"
    assert classify_result(core_pass=True, comment_pass=True) == "完整通过"
    assert classify_result(core_pass=False, comment_pass=False) == "失败"


def test_render_report_includes_pass_fail_and_blockers() -> None:
    markdown = render_report(
        run_id="verify-review-flow-20260101010101-abc12345",
        conclusion="核心通过",
        passed_items=["review_record 新增", "review_status 流转"],
        failed_items=["GitHub comment 未确认"],
        blockers=["Redis 队列已空，当前任务可能已被旧 worker 消费"],
    )

    assert "核心通过" in markdown
    assert "GitHub comment 未确认" in markdown
    assert "Redis 队列已空" in markdown


def test_render_report_includes_git_and_observation_details() -> None:
    markdown = render_report(
        run_id="verify-review-flow-20260101010101-abc12345",
        conclusion="完整通过",
        passed_items=["完整链路通过"],
        failed_items=[],
        blockers=[],
        git_commands=[
            GitCommandResult(
                args=["git", "push", "-u", "origin", "verify/review-flow/x"],
                returncode=0,
                stdout="push ok",
                stderr="",
            )
        ],
        observation_before=ObservationSnapshot(redis_queue_length=1),
        observation_after=ObservationSnapshot(
            redis_queue_length=0,
            matched_review_record={
                "id": 88,
                "branch": "verify/review-flow/x",
                "review_status": "reviewed",
                "delivery_status": "delivered",
            },
            worker_stdout="worker finished",
            github_comment_status="confirmed",
        ),
    )

    assert "git push -u origin verify/review-flow/x" in markdown
    assert "reviewed" in markdown
    assert "worker finished" in markdown
    assert "confirmed" in markdown


def test_write_report_to_path(tmp_path) -> None:
    output_path = tmp_path / "report.md"

    written_path = Path(
        write_report(
            output_path=output_path,
            content="# report",
        )
    )

    assert written_path == output_path
    assert output_path.read_text(encoding="utf-8") == "# report"


def test_fetch_latest_review_records_returns_latest_records(db_session) -> None:
    template = ProjectTemplate(
        name="Verifier Template",
        code="verifier-template",
        description="Template for verifier tests",
        file_extensions=[".py"],
        review_prompt_template="review verifier changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Verifier Project",
        key="verifier-project",
        platform_type="github",
        repo_url="https://github.example.com/acme/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={"external_repo_full_name": "acme/repo"},
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)

    first = ReviewRecord(
        project_id=project.id,
        event_type="push",
        platform_type="github",
        external_event_id="event-1",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author="alice",
        title="first",
        branch="feature/one",
        review_status="queued",
        delivery_status="pending",
        webhook_data={},
        extra_data={},
    )
    second = ReviewRecord(
        project_id=project.id,
        event_type="push",
        platform_type="github",
        external_event_id="event-2",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author="bob",
        title="second",
        branch="feature/two",
        review_status="reviewed",
        delivery_status="delivered",
        webhook_data={},
        extra_data={},
    )
    db_session.add_all([first, second])
    db_session.commit()

    snapshots = fetch_latest_review_records(db_session, limit=2)

    assert [item["external_event_id"] for item in snapshots] == ["event-2", "event-1"]
    assert snapshots[0]["review_status"] == "reviewed"
    assert snapshots[0]["delivery_status"] == "delivered"
    assert snapshots[0]["branch"] == "feature/two"
    assert "webhook_data" in snapshots[0]


def test_fetch_redis_queue_length_and_head() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.values = {"review:jobs": ['{"review_record_id":1}']}

        async def llen(self, key: str) -> int:
            return len(self.values.get(key, []))

        async def lindex(self, key: str, index: int) -> str | None:
            items = self.values.get(key, [])
            if not items:
                return None
            return items[index]

    redis_client = FakeRedis()

    assert fetch_redis_queue_length(redis_client, "review:jobs") == 1
    assert fetch_redis_queue_head(redis_client, "review:jobs") == '{"review_record_id":1}'


def test_observation_snapshot_defaults() -> None:
    snapshot = ObservationSnapshot()

    assert snapshot.review_records == []
    assert snapshot.matched_review_record is None
    assert snapshot.redis_queue_length is None


def test_patch_and_restore_readme(tmp_path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("hello\n", encoding="utf-8")

    original, updated = patch_readme(readme_path, "verify-review-flow-test")

    assert original == "hello\n"
    assert "verify-review-flow-test" in updated
    assert readme_path.read_text(encoding="utf-8") == updated

    restore_readme(readme_path, original)
    assert readme_path.read_text(encoding="utf-8") == "hello\n"


def test_collect_observation_snapshot_merges_db_and_redis(db_session) -> None:
    template = ProjectTemplate(
        name="Snapshot Template",
        code="snapshot-template",
        description="Template for snapshot tests",
        file_extensions=[".py"],
        review_prompt_template="review snapshot changes",
        prompt_metadata={"language": "zh-CN"},
        is_system=False,
        is_active=True,
    )
    project = Project(
        name="Snapshot Project",
        key="snapshot-project",
        platform_type="github",
        repo_url="https://github.example.com/acme/repo",
        default_branch="main",
        review_enabled=True,
        template=template,
        settings={"external_repo_full_name": "acme/repo"},
    )
    db_session.add_all([template, project])
    db_session.commit()
    db_session.refresh(project)

    record = ReviewRecord(
        project_id=project.id,
        event_type="push",
        platform_type="github",
        external_event_id="snapshot-event",
        project_name_snapshot=project.name,
        template_id_snapshot=project.template_id,
        template_name_snapshot=project.template.name,
        review_prompt_snapshot=project.template.review_prompt_template,
        author="alice",
        title="snapshot",
        branch="feature/snapshot",
        review_status="queued",
        delivery_status="pending",
        webhook_data={},
        extra_data={},
    )
    db_session.add(record)
    db_session.commit()

    class FakeRedis:
        async def llen(self, key: str) -> int:
            return 2 if key == "review:jobs" else 0

        async def lindex(self, key: str, index: int) -> str | None:
            if key == "review:jobs" and index == 0:
                return '{"review_record_id":999}'
            return None

    snapshot = collect_observation_snapshot(
        db_session,
        redis_client=FakeRedis(),
        queue_name="review:jobs",
        limit=1,
    )

    assert snapshot.redis_queue_length == 2
    assert snapshot.redis_queue_head == '{"review_record_id":999}'
    assert snapshot.review_records[0]["external_event_id"] == "snapshot-event"


def test_collect_runtime_observation_uses_session_factory_and_queue_defaults() -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def scalars(self, statement):
            del statement

            class Result:
                def all(self_inner):
                    return []

            return Result()

    class FakeRedis:
        async def llen(self, key: str) -> int:
            assert key == "review:jobs"
            return 3

        async def lindex(self, key: str, index: int) -> str | None:
            assert key == "review:jobs"
            assert index == 0
            return '{"review_record_id":42}'

    snapshot = collect_runtime_observation(
        session_factory=lambda: FakeSession(),
        redis_client=FakeRedis(),
        queue_name="review:jobs",
        limit=5,
    )

    assert snapshot.redis_queue_length == 3
    assert snapshot.redis_queue_head == '{"review_record_id":42}'
    assert snapshot.review_records == []


def test_find_matching_review_record_prefers_target_branch() -> None:
    records = [
        {"id": 1, "branch": "feature/one", "review_status": "queued"},
        {"id": 2, "branch": "verify/review-flow/test-run", "review_status": "reviewed"},
    ]

    matched = find_matching_review_record(
        records,
        branch_name="verify/review-flow/test-run",
    )

    assert matched is not None
    assert matched["id"] == 2


def test_wait_for_review_outcome_polls_until_review_is_terminal(tmp_path, monkeypatch) -> None:
    import scripts.verify_full_review_flow as verifier
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan

    context = ExecutionContext(
        repo_root=tmp_path,
        backend_root=tmp_path / "backend",
        branch_prefix="verify/review-flow",
        report_path=tmp_path / "report.md",
        timeout_seconds=2,
        poll_interval=0.0,
        skip_comment_check=True,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/test-run",
        worker_manager=WorkerProcessManager(command=["python"]),
    )
    snapshots = [
        ObservationSnapshot(
            review_records=[],
            matched_review_record=None,
        ),
        ObservationSnapshot(
            review_records=[],
            matched_review_record={
                "id": 9,
                "branch": "verify/review-flow/test-run",
                "review_status": "queued",
                "delivery_status": "pending",
            },
        ),
        ObservationSnapshot(
            review_records=[],
            matched_review_record={
                "id": 9,
                "branch": "verify/review-flow/test-run",
                "review_status": "reviewed",
                "delivery_status": "delivered",
            },
        ),
    ]

    monkeypatch.setattr(verifier, "collect_runtime_observation", lambda **kwargs: snapshots.pop(0))
    monkeypatch.setattr(verifier.time, "sleep", lambda seconds: None)

    result = wait_for_review_outcome(plan)

    assert result.matched_review_record is not None
    assert result.matched_review_record["review_status"] == "reviewed"


def test_check_github_comment_status_confirms_push_comment(monkeypatch) -> None:
    record = {
        "platform_type": "github",
        "event_type": "push",
        "last_commit_id": "abc123",
        "webhook_data": {
            "repository": {
                "full_name": "acme/repo",
                "html_url": "https://github.com/acme/repo",
            }
        },
    }

    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "test-token")

    status = check_github_comment_status(
        record,
        request_json=lambda url: [
            {
                "body": "Auto Review Result: \nLooks good",
                "created_at": "2026-05-31T10:00:00Z",
            }
        ],
    )

    assert status == "confirmed"


def test_check_github_comment_status_returns_not_found_when_no_review_comment(monkeypatch) -> None:
    record = {
        "platform_type": "github",
        "event_type": "push",
        "last_commit_id": "abc123",
        "webhook_data": {
            "repository": {
                "full_name": "acme/repo",
                "html_url": "https://github.com/acme/repo",
            }
        },
    }

    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "test-token")

    status = check_github_comment_status(
        record,
        request_json=lambda url: [
            {
                "body": "ordinary comment",
                "created_at": "2026-05-31T10:00:00Z",
            }
        ],
    )

    assert status == "not_found"


def test_check_github_comment_status_skips_non_github_record() -> None:
    status = check_github_comment_status(
        {
            "platform_type": "gitlab",
            "event_type": "push",
            "last_commit_id": "abc123",
            "webhook_data": {},
        }
    )

    assert status == "skipped"


def test_run_git_command_captures_output(tmp_path) -> None:
    result = run_git_command(
        ["python", "-c", "print('hello')"],
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "hello"
    assert result.stderr == ""


def test_execution_context_defaults() -> None:
    from scripts.verify_full_review_flow import ExecutionContext

    context = ExecutionContext(
        repo_root=Path("/tmp/repo"),
        backend_root=Path("/tmp/backend"),
        branch_prefix="verify/review-flow",
        report_path=Path("/tmp/report.md"),
    )

    assert context.branch_prefix == "verify/review-flow"
    assert context.skip_comment_check is False


def test_execution_result_records_summary() -> None:
    from scripts.verify_full_review_flow import ExecutionResult

    result = ExecutionResult(
        run_id="verify-review-flow-1",
        conclusion="核心通过",
        report_path=Path("/tmp/report.md"),
        preflight=run_preflight_checks(repo_root="/tmp/repo", backend_root="/tmp/backend"),
        observation_before=ObservationSnapshot(),
        observation_after=ObservationSnapshot(),
        git_commands=[],
        worker_manager=WorkerProcessManager(command=["python"]),
    )

    assert result.conclusion == "核心通过"
    assert result.git_commands == []


def test_parse_args_and_build_execution_context(tmp_path) -> None:
    from scripts.verify_full_review_flow import _parse_args, build_execution_context

    args = _parse_args(
        [
            "--repo-root",
            str(tmp_path),
            "--backend-root",
            str(tmp_path / "backend"),
            "--report-path",
            str(tmp_path / "report.md"),
            "--base-branch",
            "feature/main",
            "--project-id",
            "5",
            "--project-key",
            "demo-project",
            "--timeout-seconds",
            "120",
            "--poll-interval",
            "2.5",
            "--readme-path",
            str(tmp_path / "README.md"),
            "--skip-comment-check",
        ]
    )

    context = build_execution_context(args)

    assert context.base_branch == "feature/main"
    assert context.project_id == 5
    assert context.project_key == "demo-project"
    assert context.timeout_seconds == 120
    assert context.poll_interval == 2.5
    assert context.skip_comment_check is True


def test_build_execution_plan_uses_context_defaults(tmp_path) -> None:
    import sys
    from scripts.verify_full_review_flow import build_execution_context
    from scripts.verify_full_review_flow import _parse_args

    args = _parse_args(
        [
            "--repo-root",
            str(tmp_path),
            "--backend-root",
            str(tmp_path / "backend"),
            "--report-path",
            str(tmp_path / "report.md"),
        ]
    )
    context = build_execution_context(args)
    plan = build_execution_plan(context)

    assert plan.context == context
    assert plan.branch_name.startswith("verify/review-flow/")
    assert plan.worker_manager.is_configured() is True
    assert plan.worker_manager.command[0] == sys.executable


def test_build_execution_result_preserves_snapshots(tmp_path) -> None:
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan

    context = ExecutionContext(
        repo_root=tmp_path,
        backend_root=tmp_path / "backend",
        branch_prefix="verify/review-flow",
        report_path=tmp_path / "report.md",
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/verify-review-flow-1",
        worker_manager=WorkerProcessManager(command=["python"]),
    )
    preflight = run_preflight_checks(repo_root="/tmp/repo", backend_root="/tmp/backend")
    before = ObservationSnapshot(redis_queue_length=1)
    after = ObservationSnapshot(redis_queue_length=0)

    result = build_execution_result(
        plan,
        preflight=preflight,
        observation_before=before,
        observation_after=after,
        git_commands=[],
    )

    assert result.run_id == "verify-review-flow-1"
    assert result.observation_before.redis_queue_length == 1
    assert result.observation_after.redis_queue_length == 0


def test_analyze_execution_result_reports_core_status(tmp_path) -> None:
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan
    from scripts.verify_full_review_flow import PreflightResult

    context = ExecutionContext(
        repo_root=tmp_path,
        backend_root=tmp_path / "backend",
        branch_prefix="verify/review-flow",
        report_path=tmp_path / "report.md",
        skip_comment_check=True,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/test-run",
        worker_manager=WorkerProcessManager(command=["python"]),
    )
    result = build_execution_result(
        plan,
        preflight=PreflightResult(ok=True),
        observation_before=ObservationSnapshot(redis_queue_length=1),
        observation_after=ObservationSnapshot(
            redis_queue_length=0,
            matched_review_record={
                "id": 11,
                "branch": "verify/review-flow/test-run",
                "review_status": "reviewed",
                "delivery_status": "delivered",
            },
        ),
        git_commands=[
            GitCommandResult(args=["git", "push"], returncode=0, stdout="ok", stderr="")
        ],
        conclusion="核心通过",
    )

    passed_items, failed_items, blockers = analyze_execution_result(result)

    assert "git 命令全部成功" in passed_items
    assert "review_record 已入库" in passed_items
    assert failed_items == []
    assert blockers == []


def test_prepare_local_git_change_creates_branch_and_commit(tmp_path) -> None:
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan

    repo_root = tmp_path / "repo"
    backend_root = repo_root / "backend"
    repo_root.mkdir()
    backend_root.mkdir()
    readme_path = repo_root / "README.md"
    readme_path.write_text("root readme\n", encoding="utf-8")

    assert run_git_command(["git", "init", "-b", "main"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.name", "Codex Tester"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.email", "codex@example.com"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "add", "README.md"], cwd=repo_root).returncode == 0
    assert (
        run_git_command(["git", "commit", "-m", "chore: initial commit"], cwd=repo_root).returncode
        == 0
    )

    context = ExecutionContext(
        repo_root=repo_root,
        backend_root=backend_root,
        branch_prefix="verify/review-flow",
        report_path=repo_root / "docs/verification/report.md",
        base_branch="main",
        readme_path=readme_path,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/verify-review-flow-1",
        worker_manager=WorkerProcessManager(command=["python"]),
    )

    git_commands = prepare_local_git_change(plan)

    current_branch = run_git_command(["git", "branch", "--show-current"], cwd=repo_root)
    latest_commit = run_git_command(["git", "log", "-1", "--pretty=%s"], cwd=repo_root)

    assert current_branch.stdout.strip() == "verify/review-flow/verify-review-flow-1"
    assert latest_commit.stdout.strip() == "test: verify full review flow"
    assert any(command.args[:3] == ["git", "checkout", "-B"] for command in git_commands)
    assert "verify:verify-review-flow-1" in readme_path.read_text(encoding="utf-8")


def test_prepare_local_git_change_restores_readme_when_commit_fails(
    tmp_path,
    monkeypatch,
) -> None:
    import scripts.verify_full_review_flow as verifier
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan, GitCommandResult

    repo_root = tmp_path / "repo"
    backend_root = repo_root / "backend"
    repo_root.mkdir()
    backend_root.mkdir()
    readme_path = repo_root / "README.md"
    readme_path.write_text("root readme\n", encoding="utf-8")

    assert run_git_command(["git", "init", "-b", "main"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.name", "Codex Tester"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.email", "codex@example.com"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "add", "README.md"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "commit", "-m", "chore: initial commit"], cwd=repo_root).returncode == 0

    context = ExecutionContext(
        repo_root=repo_root,
        backend_root=backend_root,
        branch_prefix="verify/review-flow",
        report_path=repo_root / "docs/verification/report.md",
        base_branch="main",
        readme_path=readme_path,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/verify-review-flow-1",
        worker_manager=WorkerProcessManager(command=["python"]),
    )

    original_run_git_command = verifier.run_git_command

    def fake_run_git_command(args: list[str], *, cwd: Path | None = None) -> GitCommandResult:
        if args[:2] == ["git", "commit"]:
            return GitCommandResult(
                args=list(args),
                returncode=1,
                stdout="",
                stderr="commit failed",
            )
        return original_run_git_command(args, cwd=cwd)

    monkeypatch.setattr(verifier, "run_git_command", fake_run_git_command)
    git_commands = prepare_local_git_change(plan)

    assert git_commands[-1].returncode != 0
    assert readme_path.read_text(encoding="utf-8") == "root readme\n"


def test_push_verification_branch_uses_origin_remote(tmp_path) -> None:
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan

    remote_repo = tmp_path / "remote.git"
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "backend"
    readme_path = repo_root / "README.md"

    assert (
        run_git_command(["git", "init", "--bare", str(remote_repo)], cwd=tmp_path).returncode
        == 0
    )
    repo_root.mkdir()
    backend_root.mkdir()
    readme_path.write_text("root readme\n", encoding="utf-8")

    assert run_git_command(["git", "init", "-b", "main"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.name", "Codex Tester"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "config", "user.email", "codex@example.com"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "remote", "add", "origin", str(remote_repo)], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "add", "README.md"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "commit", "-m", "chore: initial commit"], cwd=repo_root).returncode == 0
    assert run_git_command(["git", "push", "-u", "origin", "main"], cwd=repo_root).returncode == 0

    context = ExecutionContext(
        repo_root=repo_root,
        backend_root=backend_root,
        branch_prefix="verify/review-flow",
        report_path=repo_root / "docs/verification/report.md",
        base_branch="main",
        readme_path=readme_path,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/verify-review-flow-1",
        worker_manager=WorkerProcessManager(command=["python"]),
    )

    prepare_local_git_change(plan)
    push_result = push_verification_branch(plan)
    ls_remote = run_git_command(
        ["git", "ls-remote", "--heads", "origin", plan.branch_name],
        cwd=repo_root,
    )

    assert push_result.returncode == 0
    assert plan.branch_name in ls_remote.stdout


def test_main_writes_report_when_preflight_fails(tmp_path, monkeypatch) -> None:
    from scripts.verify_full_review_flow import main

    monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)
    report_path = tmp_path / "docs/verification/report.md"

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--backend-root",
            str(tmp_path / "backend"),
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 1
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "GITHUB_ACCESS_TOKEN" in content
    assert "失败" in content


def test_main_runs_local_change_and_push_when_preflight_passes(tmp_path, monkeypatch) -> None:
    import scripts.verify_full_review_flow as verifier
    from scripts.verify_full_review_flow import GitCommandResult

    report_path = tmp_path / "docs/verification/report.md"
    backend_root = tmp_path / "backend"
    backend_root.mkdir()
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "test-token")

    captured: dict[str, object] = {}

    def fake_prepare(plan):
        captured["prepare_plan"] = plan
        return [
            GitCommandResult(
                args=["git", "commit"],
                returncode=0,
                stdout="commit ok",
                stderr="",
            )
        ]

    def fake_push(plan):
        captured["push_plan"] = plan
        return GitCommandResult(
            args=["git", "push"],
            returncode=0,
            stdout="push ok",
            stderr="",
        )

    monkeypatch.setattr(verifier, "prepare_local_git_change", fake_prepare)
    monkeypatch.setattr(verifier, "push_verification_branch", fake_push)
    monkeypatch.setattr(
        verifier.WorkerProcessManager,
        "start",
        lambda self: None,
    )
    monkeypatch.setattr(
        verifier.WorkerProcessManager,
        "stop",
        lambda self, timeout_seconds=10.0: None,
    )
    monkeypatch.setattr(
        verifier,
        "collect_runtime_observation",
        lambda: ObservationSnapshot(redis_queue_length=1),
    )
    monkeypatch.setattr(
        verifier,
        "wait_for_review_outcome",
        lambda plan: ObservationSnapshot(redis_queue_length=0),
    )
    monkeypatch.setattr(
        verifier,
        "check_github_comment_status",
        lambda record: "confirmed",
    )

    exit_code = verifier.main(
        [
            "--repo-root",
            str(tmp_path),
            "--backend-root",
            str(backend_root),
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert captured["prepare_plan"] == captured["push_plan"]
    content = report_path.read_text(encoding="utf-8")
    assert "完整通过" in content


def test_execute_plan_starts_and_stops_worker(tmp_path, monkeypatch) -> None:
    import scripts.verify_full_review_flow as verifier
    from scripts.verify_full_review_flow import ExecutionContext, ExecutionPlan, PreflightResult

    report_path = tmp_path / "docs/verification/report.md"
    backend_root = tmp_path / "backend"
    backend_root.mkdir()
    context = ExecutionContext(
        repo_root=tmp_path,
        backend_root=backend_root,
        branch_prefix="verify/review-flow",
        report_path=report_path,
    )
    plan = ExecutionPlan(
        context=context,
        run_id="verify-review-flow-1",
        branch_name="verify/review-flow/verify-review-flow-1",
        worker_manager=WorkerProcessManager(command=["python"]),
    )

    events: list[str] = []
    observations = [
        ObservationSnapshot(redis_queue_length=1),
        ObservationSnapshot(redis_queue_length=0),
    ]

    monkeypatch.setattr(
        verifier.WorkerProcessManager,
        "start",
        lambda self: events.append("start"),
    )
    monkeypatch.setattr(
        verifier.WorkerProcessManager,
        "stop",
        lambda self, timeout_seconds=10.0: events.append("stop"),
    )
    monkeypatch.setattr(
        verifier,
        "run_preflight_checks",
        lambda *, repo_root, backend_root: PreflightResult(ok=True),
    )
    monkeypatch.setattr(
        verifier,
        "prepare_local_git_change",
        lambda current_plan: [
            verifier.GitCommandResult(
                args=["git", "commit"],
                returncode=0,
                stdout="commit ok",
                stderr="",
            )
        ],
    )
    monkeypatch.setattr(
        verifier,
        "push_verification_branch",
        lambda current_plan: verifier.GitCommandResult(
            args=["git", "push"],
            returncode=0,
            stdout="push ok",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        verifier,
        "collect_runtime_observation",
        lambda: observations.pop(0),
    )
    monkeypatch.setattr(
        verifier,
        "wait_for_review_outcome",
        lambda current_plan: ObservationSnapshot(
            redis_queue_length=0,
            matched_review_record={
                "id": 21,
                "platform_type": "github",
                "event_type": "push",
                "branch": current_plan.branch_name,
                "review_status": "reviewed",
                "delivery_status": "delivered",
                "last_commit_id": "abc123",
                "webhook_data": {
                    "repository": {
                        "full_name": "acme/repo",
                        "html_url": "https://github.com/acme/repo",
                    }
                },
            },
        ),
    )
    monkeypatch.setattr(
        verifier,
        "check_github_comment_status",
        lambda record: "confirmed",
    )

    result = execute_plan(plan)

    assert events == ["start", "stop"]
    assert result.conclusion == "完整通过"
    assert result.observation_before.redis_queue_length == 1
    assert result.observation_after.redis_queue_length == 0
    assert result.observation_after.github_comment_status == "confirmed"
