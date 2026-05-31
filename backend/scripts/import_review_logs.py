from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SOURCE_LABEL = "historical_json_import"
DEFAULT_SKIPPED_PROJECT_NAMES = {"repo"}
MAX_PROJECT_PAGE_SIZE = 100


@dataclass(frozen=True)
class ImportJob:
    """描述一条待发送的导入请求。"""

    event_type: str
    source_id: int | str
    project_name: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ImportPlan:
    """聚合待导入请求与被跳过记录。"""

    requests: list[ImportJob]
    skipped_records: list[dict[str, Any]]


@dataclass(frozen=True)
class ImportResult:
    """记录单条导入请求的接口响应摘要。"""

    event_type: str
    source_id: int | str
    project_name: str
    review_record_id: int
    status_code: int
    is_duplicate: bool


def load_json_records(file_path: Path) -> list[dict[str, Any]]:
    """读取 JSON 数组文件，并校验每一项都为对象。"""
    with file_path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, list):
        raise ValueError(f"{file_path} 必须是 JSON 数组。")

    normalized_records: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"{file_path} 第 {index + 1} 条记录不是 JSON 对象。")
        normalized_records.append(item)
    return normalized_records


def split_commit_messages(value: Any) -> list[str]:
    """将以分号拼接的 commit message 拆成列表。"""
    if value in (None, ""):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def derive_url_slug(url: Any) -> str | None:
    """从 MR URL 提取稳定的路径片段。"""
    if not isinstance(url, str) or not url.strip():
        return None
    parsed_url = parse.urlparse(url.strip())
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if not path_parts:
        return None
    return "/".join(path_parts)


def normalize_agent_trace(value: Any) -> dict[str, Any]:
    """兼容字符串、空值和对象形式的 agent trace。"""
    if isinstance(value, dict):
        return value
    if value in (None, "", []):
        return {}
    return {"raw": value}


def build_commit_payloads(
    *,
    event_prefix: str,
    source_record: dict[str, Any],
) -> list[dict[str, Any]]:
    """把源记录里的 commit_messages 转成 mock-ingest 接口需要的 commits 数组。"""
    messages = split_commit_messages(source_record.get("commit_messages"))
    commit_payloads: list[dict[str, Any]] = []
    last_commit_id = source_record.get("last_commit_id")
    source_id = source_record.get("id")
    for index, message in enumerate(messages):
        commit_id = (
            str(last_commit_id).strip()
            if last_commit_id not in (None, "") and index == len(messages) - 1
            else f"{event_prefix}:{source_id}:{index + 1}"
        )
        commit_payloads.append(
            {
                "id": commit_id,
                "author": source_record.get("author"),
                "message": message,
                "timestamp": source_record.get("updated_at"),
            }
        )
    return commit_payloads


def build_mock_ingest_request(
    *,
    event_type: str,
    project_key: str,
    source_record: dict[str, Any],
    source_label: str = DEFAULT_SOURCE_LABEL,
) -> dict[str, Any]:
    """把单条源记录转换成 mock-ingest 接口请求体。"""
    event_prefix = "mr" if event_type == "merge_request" else "push"
    source_id = source_record["id"]
    payload: dict[str, Any] = {
        "external_event_id": f"{event_prefix}:{source_id}",
        "project_name": source_record.get("project_name"),
        "author": source_record.get("author"),
        "updated_at": source_record.get("updated_at"),
        "commits": build_commit_payloads(
            event_prefix=event_prefix,
            source_record=source_record,
        ),
        "score": source_record.get("score"),
        "review_result": source_record.get("review_result"),
        "additions": source_record.get("additions", 0),
        "deletions": source_record.get("deletions", 0),
        "webhook_data": source_record,
        "agent_trace": normalize_agent_trace(source_record.get("agent_trace")),
        "summary": None,
        "review_status": "reviewed",
        "delivery_status": "delivered",
    }

    if event_type == "merge_request":
        payload.update(
            {
                "source_branch": source_record.get("source_branch"),
                "target_branch": source_record.get("target_branch"),
                "url": source_record.get("url"),
                "url_slug": derive_url_slug(source_record.get("url")),
                "last_commit_id": source_record.get("last_commit_id"),
                "platform": source_record.get("platform"),
                "review_mode": source_record.get("review_mode"),
                "review_profile": source_record.get("review_profile"),
                "risk_level": source_record.get("risk_level"),
                "source_project_id": source_record.get("project_id"),
            }
        )
    else:
        payload["branch"] = source_record.get("branch")

    return {
        "event_type": event_type,
        "project_key": project_key,
        "source": source_label,
        "payload": payload,
    }


def build_import_jobs(
    *,
    merge_request_records: list[dict[str, Any]],
    push_records: list[dict[str, Any]],
    project_key_by_name: dict[str, str],
    skipped_project_names: set[str] | None = None,
    source_label: str = DEFAULT_SOURCE_LABEL,
) -> ImportPlan:
    """根据项目映射表构建导入计划，并记录无法导入的数据。"""
    skipped_names = skipped_project_names or set()
    import_jobs: list[ImportJob] = []
    skipped_records: list[dict[str, Any]] = []

    for event_type, records in (
        ("merge_request", merge_request_records),
        ("push", push_records),
    ):
        for source_record in records:
            project_name = str(source_record.get("project_name") or "").strip()
            source_id = source_record.get("id")

            if project_name in skipped_names:
                skipped_records.append(
                    {
                        "event_type": event_type,
                        "source_id": source_id,
                        "project_name": project_name,
                        "reason": "skipped_project_name",
                    }
                )
                continue

            project_key = project_key_by_name.get(project_name)
            if project_key is None:
                skipped_records.append(
                    {
                        "event_type": event_type,
                        "source_id": source_id,
                        "project_name": project_name,
                        "reason": "project_not_found",
                    }
                )
                continue

            import_jobs.append(
                ImportJob(
                    event_type=event_type,
                    source_id=source_id,
                    project_name=project_name,
                    payload=build_mock_ingest_request(
                        event_type=event_type,
                        project_key=project_key,
                        source_record=source_record,
                        source_label=source_label,
                    ),
                )
            )

    return ImportPlan(requests=import_jobs, skipped_records=skipped_records)


def _http_json_request(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    """发送 JSON HTTP 请求，并把响应解析成字典。"""
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    request_data = None
    if payload is not None:
        request_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    http_request = request.Request(
        url=url,
        data=request_data,
        headers=request_headers,
        method=method,
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_status = response.status
            raw_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        raise RuntimeError(
            f"请求失败 {method} {url} -> HTTP {exc.code}: {raw_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"请求失败 {method} {url}: {exc.reason}") from exc

    if not raw_body.strip():
        return response_status, {}

    response_body = json.loads(raw_body)
    if not isinstance(response_body, dict):
        raise RuntimeError(f"接口返回不是 JSON 对象: {url}")
    return response_status, response_body


def login_and_get_access_token(
    *,
    base_url: str,
    username: str,
    password: str,
    timeout_seconds: float,
) -> str:
    """调用登录接口获取 access token。"""
    _, response_body = _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/v1/auth/login",
        payload={"username": username, "password": password},
        timeout_seconds=timeout_seconds,
    )
    access_token = response_body.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise RuntimeError("登录成功但响应中缺少 access_token。")
    return access_token


def fetch_active_project_key_by_name(
    *,
    base_url: str,
    access_token: str,
    page_size: int,
    timeout_seconds: float,
) -> dict[str, str]:
    """分页拉取启用中的项目列表，并生成 project_name -> project_key 映射。"""
    headers = {"Authorization": f"Bearer {access_token}"}
    current_page = 1
    total = None
    effective_page_size = max(1, min(page_size, MAX_PROJECT_PAGE_SIZE))
    project_key_by_name: dict[str, str] = {}

    while total is None or (current_page - 1) * effective_page_size < total:
        query_string = parse.urlencode(
            {"page": current_page, "page_size": effective_page_size}
        )
        _, response_body = _http_json_request(
            method="GET",
            url=f"{base_url.rstrip('/')}/api/v1/projects?{query_string}",
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        items = response_body.get("items")
        if not isinstance(items, list):
            raise RuntimeError("项目列表响应缺少 items 数组。")
        raw_total = response_body.get("total")
        if not isinstance(raw_total, int):
            raise RuntimeError("项目列表响应缺少 total 字段。")
        total = raw_total

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("is_active") is not True:
                continue
            project_name = str(item.get("name") or "").strip()
            project_key = str(item.get("key") or "").strip()
            if not project_name or not project_key:
                continue
            if (
                project_name in project_key_by_name
                and project_key_by_name[project_name] != project_key
            ):
                raise RuntimeError(f"发现重名启用项目，无法自动导入: {project_name}")
            project_key_by_name[project_name] = project_key

        current_page += 1

    return project_key_by_name


def import_review_logs(
    *,
    base_url: str,
    username: str,
    password: str,
    mr_file: Path,
    push_file: Path,
    skipped_project_names: set[str],
    source_label: str,
    page_size: int,
    timeout_seconds: float,
    dry_run: bool,
) -> tuple[ImportPlan, list[ImportResult]]:
    """执行完整导入流程：登录、解析项目、读取文件并逐条导入。"""
    access_token = login_and_get_access_token(
        base_url=base_url,
        username=username,
        password=password,
        timeout_seconds=timeout_seconds,
    )
    project_key_by_name = fetch_active_project_key_by_name(
        base_url=base_url,
        access_token=access_token,
        page_size=page_size,
        timeout_seconds=timeout_seconds,
    )
    plan = build_import_jobs(
        merge_request_records=load_json_records(mr_file),
        push_records=load_json_records(push_file),
        project_key_by_name=project_key_by_name,
        skipped_project_names=skipped_project_names,
        source_label=source_label,
    )
    if dry_run:
        return plan, []

    headers = {"Authorization": f"Bearer {access_token}"}
    results: list[ImportResult] = []
    for job in plan.requests:
        status_code, response_body = _http_json_request(
            method="POST",
            url=f"{base_url.rstrip('/')}/api/v1/review-records/mock-ingest",
            payload=job.payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        review_record_id = response_body.get("id")
        is_duplicate = bool(response_body.get("is_duplicate"))
        if not isinstance(review_record_id, int):
            raise RuntimeError(
                f"导入响应缺少合法 id: event_type={job.event_type}, source_id={job.source_id}"
            )
        results.append(
            ImportResult(
                event_type=job.event_type,
                source_id=job.source_id,
                project_name=job.project_name,
                review_record_id=review_record_id,
                status_code=status_code,
                is_duplicate=is_duplicate,
            )
        )
    return plan, results


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="批量导入本地 MR / Push 审查日志。")
    parser.add_argument("--mr-file", required=True, help="MR 日志 JSON 文件路径。")
    parser.add_argument("--push-file", required=True, help="Push 日志 JSON 文件路径。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="后端服务地址。")
    parser.add_argument("--username", default="admin", help="登录用户名。")
    parser.add_argument("--password", default="jdw112233", help="登录密码。")
    parser.add_argument(
        "--skip-project-name",
        action="append",
        default=sorted(DEFAULT_SKIPPED_PROJECT_NAMES),
        help="需要跳过导入的 project_name，可重复传入。",
    )
    parser.add_argument(
        "--source-label",
        default=DEFAULT_SOURCE_LABEL,
        help="写入导入记录的 source 标识。",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=MAX_PROJECT_PAGE_SIZE,
        help="拉取项目列表时使用的分页大小。",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="单次 HTTP 请求超时时间（秒）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览导入计划，不实际调用导入接口。",
    )
    return parser


def main() -> int:
    """脚本入口。"""
    args = build_argument_parser().parse_args()
    plan, results = import_review_logs(
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        mr_file=Path(args.mr_file).expanduser().resolve(),
        push_file=Path(args.push_file).expanduser().resolve(),
        skipped_project_names={name.strip() for name in args.skip_project_name if name.strip()},
        source_label=args.source_label,
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "planned_request_count": len(plan.requests),
                "skipped_count": len(plan.skipped_records),
                "skipped_records": plan.skipped_records,
                "imported_count": len(results),
                "duplicate_count": sum(1 for result in results if result.is_duplicate),
                "created_count": sum(1 for result in results if not result.is_duplicate),
                "results": [
                    {
                        "event_type": result.event_type,
                        "source_id": result.source_id,
                        "project_name": result.project_name,
                        "review_record_id": result.review_record_id,
                        "status_code": result.status_code,
                        "is_duplicate": result.is_duplicate,
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
