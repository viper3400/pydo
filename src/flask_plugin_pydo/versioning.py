from __future__ import annotations

import os
from importlib import metadata


def resolve_plugin_version() -> str:
    override = os.getenv("PYTODO_VERSION", "").strip()
    if override:
        return override

    try:
        return metadata.version("pydo-fastapi-plugin")
    except metadata.PackageNotFoundError:
        return "local-dev"
