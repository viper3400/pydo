"""Standalone development app; run with ``uvicorn dev_app:app --reload``."""

from flask_plugin_pydo.routes import create_app

app = create_app({"PYDO_TODO_FILE": "data/todo.txt", "SECRET_KEY": "development-only-change-me"})
