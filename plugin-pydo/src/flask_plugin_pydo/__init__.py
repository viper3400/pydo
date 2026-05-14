"""PyDo plugin package."""

from flask_plugin_pydo.plugin import PLUGIN
from flask_plugin_pydo.routes import blueprint

__all__ = ["PLUGIN", "blueprint"]
