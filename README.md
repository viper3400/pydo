# PyDo FastAPI plugin

PyDo is a standalone FastAPI todo.txt application and a discoverable FeedVanta tool plugin. It has no Flask runtime or Flask-to-ASGI bridge.

## Install with FeedVanta

The `tool_host.plugins` contract currently ships with FeedVanta rather than as an independent package. Install both projects into the same environment:

```bash
uv pip install -e /path/to/feed-vanta -e /path/to/pytodo
```

FeedVanta discovers the `tool_host.plugins` entry point and mounts PyDo at `/pydo`. The host and plugin must be installed in the same Python environment. For local development:

```bash
uv sync --extra test
uv run uvicorn dev_app:app --reload
```

This development app is available at `http://127.0.0.1:8000/`; it uses `data/todo.txt`. Do not point it at a production todo file unless intended.

## Standalone app

```python
from flask_plugin_pydo import create_app

app = create_app({"PYDO_TODO_FILE": "/path/to/todo.txt", "SECRET_KEY": "replace-with-a-secret"})
```

Run it with an ASGI server such as Uvicorn. When embedding the app beneath a path, mount it as a sub-application; the host mount path is supplied by ASGI `root_path` and used for generated links. Password login also works when the host or reverse proxy serves PyDo beneath a URL prefix.

## Configuration

`create_app(settings=...)` accepts a `PydoSettings` object or mapping. Values in the mapping override environment variables.

- `PYDO_TODO_FILE`: todo file path; if unset, uses `PYDO_DATA_DIR/todo.txt`
- `PYDO_DATA_DIR`: data and login-lock directory; defaults to `~/.local/share/pydo`
- `PYDO_NOW_PROVIDER`: callable returning a `datetime`
- `PYDO_MAX_LOGIN_ATTEMPTS`: failed-login threshold (default `3`)
- `PYDO_VERSION`, then `PYTODO_VERSION`: optional footer version fallback
- `PYTODO_PASSWORD` or `PYTODO_PASSWORD_HASH`: enables authentication
- `SECRET_KEY`: required when authentication is enabled; used to sign the session cookie
- `PYTODO_SESSION_COOKIE_NAME`: cookie name (default `pytodo_session`)

Failed login counts and lock state are stored as `.auth_attempts` and `.auth_blocked` beside the todo file. Removing `.auth_blocked` on the server unlocks login. Never use a placeholder secret in production.

## Behavior

PyDo preserves todo.txt parsing, stable line-targeted edits from filtered/sorted views, project hierarchy, active section ordering, due quick actions, and allowlist-based hidden metadata. The old Flask blueprint integration has been removed; integrations must use `PLUGIN.app_factory` or `create_app` and mount the ASGI app.

## Tests and build

```bash
uv sync --extra test
uv run pytest -q
uv run python -m py_compile src/flask_plugin_pydo/*.py
uvx ruff check src/flask_plugin_pydo
uvx ruff format --check src/flask_plugin_pydo
uv build
```

To verify discovery and mounting against a local FeedVanta checkout, install both projects in the same environment and start the host. PyDo’s contract import is intentionally supplied by FeedVanta, not duplicated in this package.

## Versioning and releases

`project.version` in `pyproject.toml` is the release source of truth. Plugin release tags use `plugin-pydo-vX.Y.Z`.
