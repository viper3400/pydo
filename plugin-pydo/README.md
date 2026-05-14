# flask-plugin-pydo

Standalone `pydo` plugin package for `flask-plugin-platform`.

## What it contains

- One Flask blueprint mounted at `/pydo`
- Plugin-local templates and static assets
- File-backed todo.txt storage
- Login gate compatible with the original app's env vars
- Entry-point discovery for `flask_plugin_platform.plugins`

## Install

```bash
pip install -e ./plugin-pydo
```

## Platform editable install

```bash
pip install -e /Users/Jan/Documents/Development/pytodo/plugin-pydo
```

## Host app registration example

```python
from flask import Flask
from flask_plugin_pydo.plugin import PLUGIN

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["PYDO_TODO_FILE"] = "/absolute/path/to/data/todo.txt"
app.register_blueprint(PLUGIN["blueprint"])
```

## Config

Optional host config keys:

- `PYDO_TODO_FILE`: absolute or relative path to the todo file
- `PYDO_DATA_DIR`: directory used when `PYDO_TODO_FILE` is not set
- `PYDO_VERSION`: footer version string
- `PYDO_NOW_PROVIDER`: callable returning `datetime`

Compatible env vars preserved from the original app:

- `PYTODO_PASSWORD`
- `PYTODO_PASSWORD_HASH`
- `SECRET_KEY`
- `PYTODO_SESSION_COOKIE_NAME`
- `PYTODO_VERSION`

## Tests

```bash
PYTHONPATH=plugin-pydo/src pytest -q plugin-pydo/src/flask_plugin_pydo/tests
```
