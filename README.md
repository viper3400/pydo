# flask-plugin-pydo

`flask-plugin-pydo` is a `todo.txt` task management plugin for `flask-plugin-platform`.

## What it contains

- One Flask blueprint mounted at `/pydo`
- Plugin-local templates and static assets
- File-backed `todo.txt` storage
- Login gate compatible with the original PyTodo env vars
- Entry-point discovery for `flask_plugin_platform.plugins`

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Host app integration

```python
from flask import Flask
from flask_plugin_pydo.plugin import PLUGIN

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["PYDO_TODO_FILE"] = "/absolute/path/to/data/todo.txt"
app.register_blueprint(PLUGIN["blueprint"])
```

After registration the plugin is served at `/pydo/`.

## Config

Host config keys:

- `PYDO_TODO_FILE`: absolute or relative path to the todo file
- `PYDO_DATA_DIR`: directory used when `PYDO_TODO_FILE` is not set
- `PYDO_VERSION`: footer version string
- `PYDO_NOW_PROVIDER`: callable returning `datetime`
- `PYDO_MAX_LOGIN_ATTEMPTS`: login lock threshold, default `3`

Compatible env vars preserved from the original app:

- `PYTODO_PASSWORD`
- `PYTODO_PASSWORD_HASH`
- `SECRET_KEY`
- `PYTODO_SESSION_COOKIE_NAME`
- `PYTODO_VERSION`

## Behavior

- Stable line-based task mutation for filtered and sorted views
- Main project hierarchy with `++MainProject` and child `+Project`
- Active-section order:
  `Overdue -> Due Today -> Prioritized (no due) -> Due This Week -> Other Due Dates -> Other Tasks`
- Due quick actions remain line-targeted and repeat-safe
- Hidden display metadata is allowlist-based for `due`, `waiting`, and `link`
- Reverse-proxy-safe redirect handling for path-prefix mounts such as `/pydo`

## Testing

Run the full test suite from repo root:

```bash
pytest -q
```

Quick compile check:

```bash
python3 -m py_compile src/flask_plugin_pydo/*.py
```

Optional targeted plugin test run:

```bash
pytest -q src/flask_plugin_pydo/tests
```

## Release

Plugin package releases use tags named `plugin-pydo-vX.Y.Z`.

The GitHub release workflow:

- verifies the tag matches `project.version` in `pyproject.toml`
- builds wheel and sdist from repo root
- validates artifacts with `twine`
- publishes a GitHub release with the built distributions attached

## Repository layout

```text
.
├── src/flask_plugin_pydo/    # plugin code, templates, static assets, tests
├── pyproject.toml            # package metadata
├── CHANGELOG.md              # release history
├── AGENTS.md                 # repo agent guidance
└── README.md                 # plugin docs
```
