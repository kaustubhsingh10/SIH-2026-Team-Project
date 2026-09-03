"""Legacy API entrypoint module — Deprecated.

This module is maintained for backward compatibility with legacy test imports.
The canonical FastAPI application is located in `crimegraph.api.app:app`.
"""

from crimegraph.api.app import app, create_app

__all__ = ["app", "create_app"]
