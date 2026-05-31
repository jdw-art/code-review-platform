from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from uuid import uuid4

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from redis.asyncio import Redis
from sqlalchemy import select

from app.db.models import ReviewRecord


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkerProcessManager:
    command: list[str]
    cwd: Path | None = None
    _process: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    stdout: str = field(default="", init=False)
    stderr: str = field(default="", init=False)

    def is_configured(self) -> bool:
        return bool(self.command)

    def start(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        self._process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd) if self.cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self._process

    def stop(self, timeout_seconds: float = 10.0) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                stdout, stderr = self._process.communicate(timeout=timeout_seconds)
                self.stdout = stdout or ""
                self.stderr = stderr or ""
            except subprocess.TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate(timeout=timeout_seconds)
                self.stdout = stdout or ""
                self.stderr = stderr or ""
        else:
            stdout, stderr = self._process.communicate()
            self.stdout = stdout or ""
            self.stderr = stderr or ""


@dataclass(slots=True)
class ObservationSnapshot:
    review_records: list[dict[str, object]] = field(default_factory=list)
    matched_review_record: dict[str, object] | None = None
    redis_queue_length: int | None = None
    redis_queue_head: str | None = None
    worker_stdout: str = ""
    worker_stderr: str = ""
    github_comment_status: str | None = None


@dataclass(slots=True)
class GitCommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(slots=True)
class ExecutionContext:
    repo_root: Path
    backend_root: Path
    branch_prefix: str
    report_path: Path
    base_branch: str = "main"
    project_id: int | None = None
    project_key: str | None = None
    timeout_seconds: int = 600
    poll_interval: float = 5.0
    readme_path: Path | None = None
    skip_comment_check: bool = False


@dataclass(slots=True)
class ExecutionResult:
    run_id: str
    conclusion: str
    report_path: Path
    preflight: PreflightResult
    observation_before: ObservationSnapshot
    observation_after: ObservationSnapshot
    git_commands: list[GitCommandResult] = field(default_factory=list)
    worker_manager: WorkerProcessManager | None = None


@dataclass(slots=True)
class ExecutionPlan:
    context: ExecutionContext
    run_id: str
    branch_name: str
    worker_manager: WorkerProcessManager


def build_run_id(prefix: str) -> str:
    safe_prefix = prefix.strip().replace("/", "-").replace("_", "-")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"{safe_prefix}-{timestamp}-{suffix}"


def build_branch_name(prefix: str, run_id: str) -> str:
    return f"{prefix.rstrip('/')}/{run_id}"


def run_preflight_checks(*, repo_root: str, backend_root: str) -> PreflightResult:
    del repo_root, backend_root

    errors: list[str] = []
    if not os.getenv("GITHUB_ACCESS_TOKEN"):
        errors.append("GITHUB_ACCESS_TOKEN")

    return PreflightResult(ok=not errors, errors=errors)


def classify_result(*, core_pass: bool, comment_pass: bool) -> str:
    if not core_pass:
        return "失败"
    if comment_pass:
        return "完整通过"
    return "核心通过"


def render_report(
    *,
    run_id: str,
    conclusion: str,
    passed_items: list[str],
    failed_items: list[str],
    blockers: list[str],
    git_commands: list[GitCommandResult] | None = None,
    observation_before: ObservationSnapshot | None = None,
    observation_after: ObservationSnapshot | None = None,
) -> str:
    lines = [
        f"# Full Review Flow Verification Report",
        "",
        f"- Run ID: `{run_id}`",
        f"- Conclusion: `{conclusion}`",
        "",
        "## Passed",
    ]
    lines.extend(f"- {item}" for item in passed_items or ["(none)"])
    lines.append("")
    lines.append("## Failed")
    lines.extend(f"- {item}" for item in failed_items or ["(none)"])
    lines.append("")
    lines.append("## Blockers")
    lines.extend(f"- {item}" for item in blockers or ["(none)"])
    lines.append("")
    lines.append("## Git Commands")
    if git_commands:
        for command in git_commands:
            rendered_args = " ".join(command.args)
            lines.append(f"- `{rendered_args}` => rc={command.returncode}")
            if command.stdout.strip():
                lines.append(f"  stdout: `{command.stdout.strip()}`")
            if command.stderr.strip():
                lines.append(f"  stderr: `{command.stderr.strip()}`")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Observations")
    if observation_before is not None:
        lines.append(
            f"- Before queue length: `{observation_before.redis_queue_length}`"
        )
    if observation_after is not None:
        lines.append(
            f"- After queue length: `{observation_after.redis_queue_length}`"
        )
        lines.append(
            f"- GitHub comment status: `{observation_after.github_comment_status}`"
        )
        matched = observation_after.matched_review_record
        if matched is not None:
            lines.append(f"- Matched review record id: `{matched.get('id')}`")
            lines.append(f"- Matched review status: `{matched.get('review_status')}`")
            lines.append(f"- Matched delivery status: `{matched.get('delivery_status')}`")
        if observation_after.worker_stdout.strip():
            lines.append(f"- Worker stdout: `{observation_after.worker_stdout.strip()}`")
        if observation_after.worker_stderr.strip():
            lines.append(f"- Worker stderr: `{observation_after.worker_stderr.strip()}`")
    lines.append("")
    return "\n".join(lines)


def write_report(*, output_path: Path, content: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def fetch_latest_review_records(session, limit: int = 10) -> list[dict[str, object]]:
    records = session.scalars(
        select(ReviewRecord).order_by(
            ReviewRecord.created_at.desc(),
            ReviewRecord.id.desc(),
        ).limit(limit)
    ).all()
    return [
        {
            "id": record.id,
            "project_id": record.project_id,
            "event_type": record.event_type,
            "platform_type": record.platform_type,
            "external_event_id": record.external_event_id,
            "external_pull_request_id": record.external_pull_request_id,
            "review_status": record.review_status,
            "delivery_status": record.delivery_status,
            "score": record.score,
            "review_result": record.review_result,
            "error_message": record.error_message,
            "retry_count": record.retry_count,
            "branch": record.branch,
            "source_branch": record.source_branch,
            "target_branch": record.target_branch,
            "last_commit_id": record.last_commit_id,
            "webhook_data": record.webhook_data,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        for record in records
    ]


def _resolve_sync_awaitable(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return asyncio.run(value)
    return value


async def _fetch_redis_queue_snapshot_async(
    redis_client: Any,
    queue_name: str,
) -> tuple[int, str | None]:
    length = await redis_client.llen(queue_name)
    head = await redis_client.lindex(queue_name, 0)
    return int(length), head


async def _collect_runtime_observation_async(
    *,
    session_factory,
    redis_client: Any,
    queue_name: str,
    limit: int,
) -> ObservationSnapshot:
    try:
        with session_factory() as session:
            redis_queue_length, redis_queue_head = await _fetch_redis_queue_snapshot_async(
                redis_client,
                queue_name,
            )
            return ObservationSnapshot(
                review_records=fetch_latest_review_records(session, limit=limit),
                redis_queue_length=redis_queue_length,
                redis_queue_head=redis_queue_head,
            )
    finally:
        close = getattr(redis_client, "aclose", None)
        if callable(close):
            await close()


def fetch_redis_queue_length(redis_client: Any, queue_name: str) -> int:
    length, _ = asyncio.run(_fetch_redis_queue_snapshot_async(redis_client, queue_name))
    return length


def fetch_redis_queue_head(redis_client: Any, queue_name: str) -> str | None:
    _, head = asyncio.run(_fetch_redis_queue_snapshot_async(redis_client, queue_name))
    return head


def collect_observation_snapshot(
    session,
    *,
    redis_client: Any,
    queue_name: str,
    limit: int = 10,
) -> ObservationSnapshot:
    redis_queue_length, redis_queue_head = asyncio.run(
        _fetch_redis_queue_snapshot_async(redis_client, queue_name)
    )
    return ObservationSnapshot(
        review_records=fetch_latest_review_records(session, limit=limit),
        redis_queue_length=redis_queue_length,
        redis_queue_head=redis_queue_head,
    )


def find_matching_review_record(
    review_records: list[dict[str, object]],
    *,
    branch_name: str,
) -> dict[str, object] | None:
    for record in review_records:
        if record.get("branch") == branch_name:
            return record
        if record.get("source_branch") == branch_name:
            return record
    return None


def collect_runtime_observation(
    *,
    session_factory=None,
    redis_client: Any | None = None,
    queue_name: str | None = None,
    limit: int = 10,
) -> ObservationSnapshot:
    if session_factory is None:
        from app.db.session import SessionLocal  # noqa: PLC0415

        session_factory = SessionLocal
    if redis_client is None:
        from app.services.auth_service import get_settings  # noqa: PLC0415

        settings = get_settings()
        redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
    if queue_name is None:
        from app.services.auth_service import get_settings  # noqa: PLC0415

        queue_name = get_settings().review_queue_name

    snapshot = asyncio.run(
        _collect_runtime_observation_async(
            session_factory=session_factory,
            redis_client=redis_client,
            queue_name=queue_name,
            limit=limit,
        )
    )
    return snapshot


def wait_for_review_outcome(plan: ExecutionPlan) -> ObservationSnapshot:
    deadline = time.monotonic() + max(plan.context.timeout_seconds, 0)
    latest_snapshot = ObservationSnapshot()
    terminal_review_statuses = {"reviewed", "failed", "skipped"}

    while True:
        latest_snapshot = collect_runtime_observation()
        latest_snapshot.matched_review_record = find_matching_review_record(
            latest_snapshot.review_records,
            branch_name=plan.branch_name,
        ) or latest_snapshot.matched_review_record

        matched = latest_snapshot.matched_review_record
        if matched is not None and matched.get("review_status") in terminal_review_statuses:
            return latest_snapshot

        if time.monotonic() >= deadline:
            return latest_snapshot

        time.sleep(plan.context.poll_interval)


def _request_github_json(url: str) -> Any:
    token = os.getenv("GITHUB_ACCESS_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing GitHub access token")
    request = Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        if not body:
            return None
        return json.loads(body)


def _resolve_github_api_base_url(record: dict[str, object]) -> str:
    repository = record.get("webhook_data") if isinstance(record.get("webhook_data"), dict) else {}
    repository_data = repository.get("repository") if isinstance(repository, dict) else {}
    if isinstance(repository_data, dict):
        parsed = urlsplit(str(repository_data.get("html_url") or ""))
        if parsed.hostname == "github.com":
            return "https://api.github.com"
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/api/v3"
    return os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")


def _resolve_github_repo_full_name(record: dict[str, object]) -> str | None:
    webhook_data = record.get("webhook_data")
    if isinstance(webhook_data, dict):
        repository = webhook_data.get("repository")
        if isinstance(repository, dict):
            repo_full_name = repository.get("full_name")
            if repo_full_name:
                return str(repo_full_name)
    return None


def _resolve_github_pull_request_id(record: dict[str, object]) -> str | None:
    pr_id = record.get("external_pull_request_id")
    if pr_id:
        return str(pr_id)
    webhook_data = record.get("webhook_data")
    if isinstance(webhook_data, dict):
        pull_request = webhook_data.get("pull_request")
        if isinstance(pull_request, dict):
            number = pull_request.get("number") or pull_request.get("id")
            if number:
                return str(number)
    return None


def _contains_auto_review_comment(comments: Any) -> bool:
    if not isinstance(comments, list):
        return False
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = str(comment.get("body") or "")
        if body.startswith("Auto Review Result:"):
            return True
    return False


def check_github_comment_status(
    record: dict[str, object] | None,
    *,
    request_json=None,
) -> str:
    if not isinstance(record, dict):
        return "not_checked"
    if str(record.get("platform_type") or "") != "github":
        return "skipped"

    repo_full_name = _resolve_github_repo_full_name(record)
    if not repo_full_name:
        return "missing_repo"

    api_base_url = _resolve_github_api_base_url(record)
    requester = request_json or _request_github_json
    event_type = str(record.get("event_type") or "")

    if event_type == "push":
        commit_id = str(record.get("last_commit_id") or "")
        if not commit_id:
            return "missing_commit"
        comments = requester(
            f"{api_base_url}/repos/{repo_full_name}/commits/{commit_id}/comments"
        )
        return "confirmed" if _contains_auto_review_comment(comments) else "not_found"

    if event_type == "pull_request":
        pull_request_id = _resolve_github_pull_request_id(record)
        if not pull_request_id:
            return "missing_pull_request"
        comments = requester(
            f"{api_base_url}/repos/{repo_full_name}/issues/{pull_request_id}/comments"
        )
        return "confirmed" if _contains_auto_review_comment(comments) else "not_found"

    return "skipped"


def run_git_command(args: list[str], *, cwd: Path | None = None) -> GitCommandResult:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return GitCommandResult(
        args=list(args),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def patch_readme(readme_path: Path, run_id: str) -> tuple[str, str]:
    original = readme_path.read_text(encoding="utf-8")
    marker = f"<!-- verify:{run_id} -->"
    updated = original.rstrip() + f"\n\n{marker}\n"
    readme_path.write_text(updated, encoding="utf-8")
    return original, updated


def restore_readme(readme_path: Path, original: str) -> None:
    readme_path.write_text(original, encoding="utf-8")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify full review flow.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--backend-root", required=True)
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--branch-prefix", default="verify/review-flow")
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--project-key")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--readme-path")
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--skip-comment-check", action="store_true")
    return parser.parse_args(argv)


def build_execution_context(args: argparse.Namespace) -> ExecutionContext:
    return ExecutionContext(
        repo_root=Path(args.repo_root),
        backend_root=Path(args.backend_root),
        branch_prefix=args.branch_prefix,
        report_path=Path(args.report_path),
        base_branch=args.base_branch,
        project_id=args.project_id,
        project_key=args.project_key,
        timeout_seconds=args.timeout_seconds,
        poll_interval=args.poll_interval,
        readme_path=Path(args.readme_path) if args.readme_path else None,
        skip_comment_check=args.skip_comment_check,
    )


def build_execution_plan(context: ExecutionContext) -> ExecutionPlan:
    run_id = build_run_id(context.branch_prefix)
    branch_name = build_branch_name(context.branch_prefix, run_id)
    worker_manager = WorkerProcessManager(
        command=[sys.executable, "-m", "app.workers.review_worker"],
        cwd=context.backend_root,
    )
    return ExecutionPlan(
        context=context,
        run_id=run_id,
        branch_name=branch_name,
        worker_manager=worker_manager,
    )


def build_execution_result(
    plan: ExecutionPlan,
    *,
    preflight: PreflightResult,
    observation_before: ObservationSnapshot,
    observation_after: ObservationSnapshot,
    git_commands: list[GitCommandResult],
    conclusion: str | None = None,
) -> ExecutionResult:
    final_conclusion = conclusion or classify_result(
        core_pass=preflight.ok,
        comment_pass=not plan.context.skip_comment_check,
    )
    return ExecutionResult(
        run_id=plan.run_id,
        conclusion=final_conclusion,
        report_path=plan.context.report_path,
        preflight=preflight,
        observation_before=observation_before,
        observation_after=observation_after,
        git_commands=list(git_commands),
        worker_manager=plan.worker_manager,
    )


def analyze_execution_result(
    result: ExecutionResult,
) -> tuple[list[str], list[str], list[str]]:
    passed_items: list[str] = []
    failed_items: list[str] = []
    blockers: list[str] = []

    if result.preflight.ok:
        passed_items.append("preflight ok")
    else:
        for error in result.preflight.errors:
            failed_items.append(error)

    if result.git_commands and all(command.returncode == 0 for command in result.git_commands):
        passed_items.append("git 命令全部成功")
    elif result.git_commands:
        failed_items.append("git 命令存在失败")

    matched = result.observation_after.matched_review_record
    if matched is not None:
        passed_items.append("review_record 已入库")
        review_status = str(matched.get("review_status") or "")
        if review_status in {"reviewed", "skipped"}:
            passed_items.append(f"review_status 已流转到 {review_status}")
        elif review_status == "failed":
            failed_items.append("review_status 已流转到 failed")
        else:
            blockers.append(f"review_status 仍为 {review_status or 'unknown'}")

        delivery_status = str(matched.get("delivery_status") or "")
        if delivery_status == "delivered":
            passed_items.append("delivery_status 已流转到 delivered")
        elif delivery_status:
            blockers.append(f"delivery_status 当前为 {delivery_status}")
    else:
        blockers.append("未找到匹配的 review_record")

    if result.worker_manager is not None:
        if result.worker_manager.stdout.strip():
            passed_items.append("worker stdout 已采集")
        if result.worker_manager.stderr.strip():
            blockers.append("worker stderr 有输出，请人工确认")

    comment_status = result.observation_after.github_comment_status
    if result.conclusion == "完整通过" and comment_status == "confirmed":
        passed_items.append("GitHub comment 已确认")
    elif comment_status:
        blockers.append(f"GitHub comment 状态为 {comment_status}")

    blockers.extend(result.preflight.warnings)
    return passed_items, failed_items, blockers


def prepare_local_git_change(plan: ExecutionPlan) -> list[GitCommandResult]:
    repo_root = plan.context.repo_root
    readme_path = plan.context.readme_path or (repo_root / "README.md")
    git_commands: list[GitCommandResult] = []

    git_commands.append(
        run_git_command(
            ["git", "checkout", "-B", plan.branch_name, plan.context.base_branch],
            cwd=repo_root,
        )
    )

    original_readme, _ = patch_readme(readme_path, plan.run_id)
    relative_readme_path = readme_path.relative_to(repo_root)

    add_result = run_git_command(
        ["git", "add", str(relative_readme_path)],
        cwd=repo_root,
    )
    git_commands.append(add_result)
    if add_result.returncode != 0:
        restore_readme(readme_path, original_readme)
        return git_commands

    commit_result = run_git_command(
        ["git", "commit", "-m", "test: verify full review flow"],
        cwd=repo_root,
    )
    git_commands.append(commit_result)
    if commit_result.returncode != 0:
        restore_readme(readme_path, original_readme)

    return git_commands


def push_verification_branch(plan: ExecutionPlan) -> GitCommandResult:
    return run_git_command(
        ["git", "push", "-u", "origin", plan.branch_name],
        cwd=plan.context.repo_root,
    )


def execute_plan(plan: ExecutionPlan) -> ExecutionResult:
    context = plan.context
    preflight = run_preflight_checks(
        repo_root=str(context.repo_root),
        backend_root=str(context.backend_root),
    )
    git_commands: list[GitCommandResult] = []
    observation_before = ObservationSnapshot()
    observation_after = ObservationSnapshot()
    worker_started = False

    try:
        if preflight.ok:
            observation_before = collect_runtime_observation()
            plan.worker_manager.start()
            worker_started = True

            git_commands.extend(prepare_local_git_change(plan))
            if git_commands and git_commands[-1].returncode == 0:
                git_commands.append(push_verification_branch(plan))
            observation_after = wait_for_review_outcome(plan)
            if not context.skip_comment_check:
                observation_after.github_comment_status = check_github_comment_status(
                    observation_after.matched_review_record
                )

        core_pass = preflight.ok and bool(git_commands or preflight.ok)
        if git_commands:
            core_pass = preflight.ok and all(
                command.returncode == 0 for command in git_commands
            )
        comment_pass = context.skip_comment_check or (
            observation_after.github_comment_status == "confirmed"
        )

        return build_execution_result(
            plan,
            preflight=preflight,
            observation_before=observation_before,
            observation_after=observation_after,
            git_commands=git_commands,
            conclusion=classify_result(
                core_pass=core_pass,
                comment_pass=core_pass and comment_pass,
            ),
        )
    finally:
        if worker_started:
            plan.worker_manager.stop()
            observation_after.worker_stdout = plan.worker_manager.stdout
            observation_after.worker_stderr = plan.worker_manager.stderr


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    context = build_execution_context(args)
    plan = build_execution_plan(context)
    result = execute_plan(plan)
    passed_items, failed_items, blockers = analyze_execution_result(result)
    report = render_report(
        run_id=result.run_id,
        conclusion=result.conclusion,
        passed_items=passed_items,
        failed_items=failed_items,
        blockers=blockers,
        git_commands=result.git_commands,
        observation_before=result.observation_before,
        observation_after=result.observation_after,
    )
    write_report(output_path=result.report_path, content=report)
    return 0 if result.preflight.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
