from __future__ import annotations

import os
from pathlib import Path

from app.core.config import BACKEND_DIR


def load_backend_env_compat(*, backend_dir: Path | None = None) -> None:
    env_file = (backend_dir or BACKEND_DIR) / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue

        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[env_key] = value
