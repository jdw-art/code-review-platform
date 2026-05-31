import subprocess
import sys
from pathlib import Path


def test_verify_full_review_flow_module_imports() -> None:
    import scripts.verify_full_review_flow  # noqa: F401


def test_verify_full_review_flow_cli_help_runs_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    script_path = backend_root / "scripts" / "verify_full_review_flow.py"

    completed = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Verify full review flow." in completed.stdout
