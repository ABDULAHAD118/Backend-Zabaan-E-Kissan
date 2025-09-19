"""
App package initializer.

- Re-exports the FastAPI `app` instance for ASGI servers.
- Provides a simple `get_app()` factory.
- Contains package metadata.
"""

from typing import Any
from fastapi import FastAPI

from .api import app  # The FastAPI instance defined in api.py

__all__ = ["app", "get_app", "__version__"]
__version__ = "1.0.0"


def get_app() -> FastAPI:
    """
    Return the FastAPI application instance.

    Useful for ASGI servers or tooling that expects a callable to obtain the app.
    """
    return app