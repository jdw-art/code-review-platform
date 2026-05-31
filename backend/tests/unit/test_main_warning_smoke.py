import pytest

import app.main as app_main


class StubSettings:
    dev_autostart_worker = False

    def uses_insecure_auth_defaults(self) -> bool:
        return True


class DevAutostartEnabledSettings(StubSettings):
    dev_autostart_worker = True


@pytest.mark.anyio
async def test_lifespan_warning_mentions_secret_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def run_test_bootstrap() -> None:
        return None

    monkeypatch.setattr(app_main, "settings", StubSettings())
    monkeypatch.setattr(app_main, "run_bootstrap", run_test_bootstrap)

    with caplog.at_level("WARNING"):
        async with app_main.lifespan(app_main.app):
            pass

    assert caplog.messages
    assert "AI_CODE_REVIEWER_SECRET_ENCRYPTION_KEY" in caplog.messages[0]


@pytest.mark.anyio
async def test_lifespan_starts_supervisor_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeSupervisor:
        def start(self) -> None:
            events.append("start")

        def stop(self) -> None:
            events.append("stop")

    async def run_test_bootstrap() -> None:
        return None

    monkeypatch.setattr(app_main, "settings", DevAutostartEnabledSettings())
    monkeypatch.setattr(app_main, "run_bootstrap", run_test_bootstrap)
    monkeypatch.setattr(app_main, "DevWorkerSupervisor", lambda **_: FakeSupervisor())

    async with app_main.lifespan(app_main.app):
        assert events == ["start"]

    assert events == ["start", "stop"]


@pytest.mark.anyio
async def test_lifespan_stops_supervisor_when_bootstrap_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeSupervisor:
        def start(self) -> None:
            events.append("start")

        def stop(self) -> None:
            events.append("stop")

    async def run_test_bootstrap() -> None:
        raise RuntimeError("bootstrap failed")

    monkeypatch.setattr(app_main, "settings", DevAutostartEnabledSettings())
    monkeypatch.setattr(app_main, "run_bootstrap", run_test_bootstrap)
    monkeypatch.setattr(app_main, "DevWorkerSupervisor", lambda **_: FakeSupervisor())

    with pytest.raises(RuntimeError, match="bootstrap failed"):
        async with app_main.lifespan(app_main.app):
            pass

    assert events == ["start", "stop"]
