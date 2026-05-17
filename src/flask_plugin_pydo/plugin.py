"""Plugin metadata exposed through Python entry points."""

from __future__ import annotations

from flask_plugin_pydo.routes import blueprint
from flask_plugin_pydo.versioning import resolve_plugin_version

PLUGIN = {
    "id": "pydo",
    "name": "PyDo",
    "description": "todo.txt task management plugin.",
    "version": resolve_plugin_version(),
    "blueprint": blueprint,
    "menu_entry": {
        "label": "PyDo",
        "icon": "check-square",
        "path": "/pydo/",
    },
}
