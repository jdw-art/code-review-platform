from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


class DevWorkerSupervisor:
    def __init__(self, *, backend_dir: Path, python_executable: str) -> None:
        self.backend_dir = backend_dir
        self.python_executable = python_executable
        self.process: subprocess.Popen[str] | None = None

    def build_command(self) -> list[str]:
        return [self.python_executable, "-m", "app.workers.review_worker"]

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        self.process = subprocess.Popen(
            self.build_command(),
            cwd=self.backend_dir,
            text=True,
            env={**os.environ, "AI_CODE_REVIEWER_MANAGED_BY_SUPERVISOR": "1"},
        )

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.send_signal(signal.SIGTERM)
        self.process.wait(timeout=10)
