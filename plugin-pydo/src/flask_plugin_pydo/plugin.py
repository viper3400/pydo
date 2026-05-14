"""Plugin metadata exposed through Python entry points."""

from __future__ import annotations

from flask_plugin_pydo.routes import blueprint

PLUGIN = {
    "id": "pydo",
    "name": "PyDo",
    "description": "todo.txt task management plugin.",
    "version": "0.1.0",
    "blueprint": blueprint,
    "menu_entry": {
        "label": "PyDo",
        "icon": "check-square",
        "path": "/pydo/",
    },
}
