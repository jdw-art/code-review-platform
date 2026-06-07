from __future__ import annotations

import re
from typing import Any


REDACTED_VALUE = "<redacted>"
SECRET_FIELD_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|token|secret|password|webhook[_ -]?secret)"
)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?im)\b(api[_ -]?key|token|secret|password|webhook[_ -]?secret)\b(\s*[:=]\s*)([^\s]+)"
)
SECRET_JSON_ASSIGNMENT_PATTERN = re.compile(
    r'(?i)("?(api[_ -]?key|token|secret|password|webhook[_ -]?secret)"?\s*:\s*)"([^"]+)"'
)
COMMON_SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----",
        re.MULTILINE,
    ),
)


def redact_text(text: str, *, secret_values: list[str]) -> str:
    output = str(text)
    values = sorted((value for value in secret_values if value), key=len, reverse=True)
    for value in values:
        output = output.replace(value, REDACTED_VALUE)
    output = SECRET_ASSIGNMENT_PATTERN.sub(r"\1\2<redacted>", output)
    output = SECRET_JSON_ASSIGNMENT_PATTERN.sub(r'\1"<redacted>"', output)
    for pattern in COMMON_SECRET_PATTERNS:
        output = pattern.sub(REDACTED_VALUE, output)
    return output


def redact_value(value: Any, *, secret_values: list[str], key: str | None = None) -> Any:
    if key and SECRET_FIELD_PATTERN.search(str(key)):
        return REDACTED_VALUE
    if isinstance(value, dict):
        return {
            str(item_key): redact_value(item_value, secret_values=secret_values, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item, secret_values=secret_values, key=key) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item, secret_values=secret_values, key=key) for item in value]
    if isinstance(value, str):
        return redact_text(value, secret_values=secret_values)
    return value
