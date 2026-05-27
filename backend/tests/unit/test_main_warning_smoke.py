import pytest

import app.main as app_main


class StubSettings:
    def uses_insecure_auth_defaults(self) -> bool:
        return True


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
