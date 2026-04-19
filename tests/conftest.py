import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as app_module


@pytest.fixture
def test_paths(tmp_path, monkeypatch):
    """Redirect runtime data files to an isolated temp directory."""
    todo_file = tmp_path / "todo.txt"
    todo_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(app_module, "TODOS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "TODOS_FILE", todo_file)
    monkeypatch.setattr(app_module, "AUTH_ATTEMPTS_FILE", tmp_path / ".auth_attempts")
    monkeypatch.setattr(app_module, "AUTH_BLOCK_FILE", tmp_path / ".auth_blocked")

    return tmp_path, todo_file


@pytest.fixture
def client(test_paths, monkeypatch):
    """Flask test client with auth disabled by default."""
    monkeypatch.setattr(app_module, "AUTH_ENABLED", False)
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    with app_module.app.test_client() as test_client:
        yield test_client
