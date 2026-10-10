"""Plugin metadata exposed through Python entry points."""

from __future__ import annotations

from tool_host.plugins import Plugin

from flask_plugin_pydo.routes import create_app
from flask_plugin_pydo.versioning import resolve_plugin_version

PLUGIN = Plugin(
    id="pydo",
    name="PyDo",
    description="todo.txt task management plugin.",
    version=resolve_plugin_version(),
    path="/pydo",
    app_factory=create_app,
)
