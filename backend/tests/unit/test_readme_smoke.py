from pathlib import Path


def test_readme_mentions_database_creation():
    content = Path("backend/README.md").read_text()

    assert "CREATE DATABASE ai_code_reviewer;" in content
    assert "redis://localhost:6379/0" in content
    assert "alembic upgrade head" in content
