from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

from app.agent.redaction import redact_text, redact_value
from app.agent.tools import TOOL_SPECS, sorted_tool_specs

MAX_READ_FILE_LINES = 200
MAX_LIST_FILES_ENTRIES = 200
MAX_SEARCH_CODE_MATCHES = 100
MAX_RESULT_CHARS = 12000
EXTERNAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


class ToolGateway:
    def __init__(
        self,
        *,
        provider,
        branch: str,
        secret_values: list[str],
        ref: str | None = None,
        project_docs_summary: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.provider = provider
        self.branch = str(branch)
        if ref is not None and not str(ref).strip():
            raise ValueError("locked ref must not be empty when provided")
        self.ref = str(ref).strip() if ref is not None else None
        self.secret_values = list(secret_values)
        self.project_docs_summary = dict(project_docs_summary or {})
        self.history: list[tuple[str, str]] = []
        self._seen_signatures: set[tuple[str, str]] = set()

    def tool_signature(self) -> str:
        payload = sorted_tool_specs()
        for item in payload:
            if item["name"] == "read_project_doc":
                item["available_names"] = sorted(self.project_docs_summary)
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def run(self, name: str, args: dict[str, object] | None) -> str:
        if name not in TOOL_SPECS:
            return f"error: unknown tool '{name}'"
        normalized_args = dict(args or {})
        canonical_args, error = self._canonicalize_args(name, normalized_args)
        if error:
            return f"error: invalid arguments for {name}: {error}"
        signature = json.dumps({"name": name, "args": canonical_args}, sort_keys=True, ensure_ascii=False)
        signature_key = (name, signature)
        if signature_key in self._seen_signatures:
            return f"error: repeated identical tool call for {name}; choose a different tool or return a final answer"
        self.history.append(signature_key)
        self._seen_signatures.add(signature_key)
        result = self._dispatch(name, canonical_args)
        if isinstance(result, dict) and result.get("error"):
            return str(result["error"])
        if isinstance(result, dict):
            result_type = str(result.get("type", "text"))
            payload = result.get("payload")
            if result_type == "json":
                return self._json_result(payload)
            return self._finalize_text(redact_text(str(payload or ""), secret_values=self.secret_values))
        return self._finalize_text(redact_text(str(result), secret_values=self.secret_values))

    def _canonicalize_args(
        self,
        name: str,
        args: dict[str, object],
    ) -> tuple[dict[str, object], str | None]:
        if name == "list_files":
            path, error = self._normalize_repo_path(args.get("path", "."), allow_dot=True)
            if error:
                return {}, error
            return {"path": path}, None
        if name == "read_file":
            path, error = self._normalize_repo_path(args.get("path", ""), allow_dot=False)
            if error:
                return {}, error
            start = self._parse_int(args.get("start", 1))
            end = self._parse_int(args.get("end", MAX_READ_FILE_LINES))
            if start is None or end is None:
                return {}, "start and end must be integers"
            if start < 1 or end < start:
                return {}, "invalid line range"
            if end - start + 1 > MAX_READ_FILE_LINES:
                return {}, f"line window exceeds maximum of {MAX_READ_FILE_LINES} lines"
            return {"path": path, "start": start, "end": end}, None
        if name == "search_code":
            query = str(args.get("query", "")).strip()
            if not query:
                return {}, "query must not be empty"
            path, error = self._normalize_repo_path(args.get("path", "."), allow_dot=True)
            if error:
                return {}, error
            return {"query": query.lower(), "path": path}, None
        if name == "read_project_doc":
            doc_name = str(args.get("name", "")).strip()
            if not doc_name:
                return {}, "name must not be empty"
            if doc_name not in self.project_docs_summary:
                return {}, f"unknown project doc '{doc_name}'"
            return {"name": doc_name}, None
        if name in {
            "get_change_summary",
            "list_commits",
            "list_comment_threads",
            "get_diff_overview",
        }:
            external_id = str(args.get("external_id", "")).strip()
            if not external_id:
                return {}, "external_id must not be empty"
            if not EXTERNAL_ID_PATTERN.fullmatch(external_id):
                return {}, "external_id has invalid format"
            return {"external_id": external_id}, None
        return {}, "unsupported tool"

    def _dispatch(self, name: str, args: dict[str, object]) -> dict[str, object]:
        if name == "list_files":
            payload = self.provider.list_tree(
                branch=self.branch,
                path=str(args.get("path", ".")),
                ref=self.ref,
            )
            entries = payload.get("entries")
            if not isinstance(entries, list):
                return {"error": "error: invalid provider result for list_files"}
            return {
                "type": "text",
                "payload": "\n".join(str(entry) for entry in entries[:MAX_LIST_FILES_ENTRIES]),
            }
        if name == "read_file":
            payload = self.provider.read_file(
                branch=self.branch,
                path=str(args["path"]),
                start=int(args.get("start", 1)),
                end=int(args.get("end", MAX_READ_FILE_LINES)),
                ref=self.ref,
            )
            return {"type": "text", "payload": str(payload.get("content", ""))}
        if name == "search_code":
            payload = self.provider.search_code(
                branch=self.branch,
                query=str(args["query"]),
                path=str(args.get("path", ".")),
                ref=self.ref,
            )
            matches = payload.get("matches")
            if not isinstance(matches, list):
                return {"error": "error: invalid provider result for search_code"}
            lines = "\n".join(
                f'{item["path"]}:{item["line"]}:{item["text"]}'
                for item in matches[:MAX_SEARCH_CODE_MATCHES]
                if isinstance(item, dict)
            )
            return {"type": "text", "payload": lines}
        if name == "read_project_doc":
            doc_name = str(args["name"]).strip()
            payload = self.project_docs_summary.get(doc_name)
            if not isinstance(payload, dict):
                return {"error": f"error: unknown project doc '{doc_name}'"}
            return {"type": "text", "payload": str(payload.get("content", ""))}
        if name == "get_change_summary":
            return {
                "type": "json",
                "payload": self.provider.get_change_summary(external_id=str(args["external_id"])),
            }
        if name == "list_commits":
            return {
                "type": "json",
                "payload": self.provider.list_commits(external_id=str(args["external_id"])),
            }
        if name == "list_comment_threads":
            return {
                "type": "json",
                "payload": self.provider.list_comment_threads(external_id=str(args["external_id"])),
            }
        if name == "get_diff_overview":
            return {
                "type": "json",
                "payload": self.provider.get_diff_overview(external_id=str(args["external_id"])),
            }
        return {"error": "error: unsupported tool"}

    @staticmethod
    def _parse_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _json_result(self, payload: Any) -> str:
        redacted = redact_value(payload, secret_values=self.secret_values)
        encoded = json.dumps(redacted, ensure_ascii=False, sort_keys=True)
        if len(encoded) <= MAX_RESULT_CHARS:
            return encoded
        summary = self._summarize_json_payload(redacted)
        return json.dumps(summary, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _normalize_repo_path(value: object, *, allow_dot: bool) -> tuple[str, str | None]:
        path = str(value).strip()
        if not path:
            return "", "path must not be empty"
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            return "", "path must stay within repository scope"
        normalized_path = str(normalized)
        if normalized_path in {"", "."}:
            if allow_dot:
                return ".", None
            return "", "path must not be empty"
        return normalized_path, None

    @staticmethod
    def _finalize_text(text: str) -> str:
        normalized = str(text)
        if len(normalized) <= MAX_RESULT_CHARS:
            return normalized
        return normalized[: MAX_RESULT_CHARS - 3] + "..."

    @staticmethod
    def _summarize_json_payload(payload: Any) -> dict[str, object]:
        if isinstance(payload, list):
            return {
                "truncated": True,
                "kind": "list",
                "item_count": len(payload),
                "preview": [ToolGateway._clip_json_value(item) for item in payload[:3]],
            }
        if isinstance(payload, dict):
            keys = sorted(str(key) for key in payload.keys())
            return {
                "truncated": True,
                "kind": "object",
                "keys": keys[:20],
                "key_count": len(keys),
                "preview": {
                    key: ToolGateway._clip_json_value(payload[key])
                    for key in list(payload)[:5]
                },
            }
        return {
            "truncated": True,
            "kind": type(payload).__name__,
            "preview": ToolGateway._clip_json_value(payload),
        }

    @staticmethod
    def _clip_json_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): ToolGateway._clip_json_value(item)
                for key, item in list(value.items())[:5]
            }
        if isinstance(value, list):
            return [ToolGateway._clip_json_value(item) for item in value[:5]]
        if isinstance(value, str):
            if len(value) <= 200:
                return value
            return value[:197] + "..."
        return value
