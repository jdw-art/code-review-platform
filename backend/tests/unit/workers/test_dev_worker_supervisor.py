from __future__ import annotations

import signal
from pathlib import Path

from app.workers.dev_worker_supervisor import DevWorkerSupervisor


def test_supervisor_builds_worker_command() -> None:
    supervisor = DevWorkerSupervisor(
        backend_dir=Path("/tmp/backend"),
        python_executable="/usr/bin/python3",
    )

    assert supervisor.build_command() == [
        "/usr/bin/python3",
        "-m",
        "app.workers.review_worker",
    ]


def test_supervisor_start_injects_managed_env(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeProcess:
        def poll(self) -> None:
            return None

    def fake_popen(command, *, cwd, text, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["text"] = text
        captured["env"] = env
        return FakeProcess()

    monkeypatch.setattr("app.workers.dev_worker_supervisor.subprocess.Popen", fake_popen)
    monkeypatch.setenv("EXISTING_ENV", "present")

    supervisor = DevWorkerSupervisor(
        backend_dir=tmp_path,
        python_executable="/usr/bin/python3",
    )

    supervisor.start()

    assert captured["command"] == [
        "/usr/bin/python3",
        "-m",
        "app.workers.review_worker",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["text"] is True
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["EXISTING_ENV"] == "present"
    assert env["AI_CODE_REVIEWER_MANAGED_BY_SUPERVISOR"] == "1"


def test_supervisor_stop_sends_sigterm_and_waits() -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.signals: list[object] = []
            self.wait_timeout: int | None = None

        def poll(self) -> None:
            return None

        def send_signal(self, sig) -> None:
            self.signals.append(sig)

        def wait(self, timeout: int) -> None:
            self.wait_timeout = timeout

    supervisor = DevWorkerSupervisor(
        backend_dir=Path("/tmp/backend"),
        python_executable="/usr/bin/python3",
    )
    process = FakeProcess()
    supervisor.process = process

    supervisor.stop()

    assert process.signals == [signal.SIGTERM]
    assert process.wait_timeout == 10
