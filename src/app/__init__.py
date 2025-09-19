"""
App package initializer.

- Re-exports the FastAPI `app` instance for ASGI servers.
- Provides a simple `get_app()` factory.
- Contains package metadata.
"""

from typing import Any
from fastapi import FastAPI

# Import the FastAPI instance from api.py
from .api import app

__all__ = ["app", "get_app", "__version__"]

__version__ = "1.0.0"


def get_app() -> FastAPI:
    """
    Return the FastAPI application instance.

    Useful for ASGI servers or tooling that expects a callable
    to obtain the app.
    """
    return app
