from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as app_main


class DevAutostartDisabledSettings:
    dev_autostart_worker = False

    def uses_insecure_auth_defaults(self) -> bool:
        return False


def test_lifespan_skips_supervisor_when_flag_disabled(
    monkeypatch,
) -> None:
    calls: list[str] = []

    class FakeSupervisor:
        def __init__(self, **_: object) -> None:
            calls.append("init")

    async def run_test_bootstrap() -> None:
        return None

    monkeypatch.setattr(app_main, "settings", DevAutostartDisabledSettings())
    monkeypatch.setattr(app_main, "run_bootstrap", run_test_bootstrap)
    monkeypatch.setattr(app_main, "DevWorkerSupervisor", FakeSupervisor)

    with TestClient(app_main.app):
        pass

    assert calls == []
