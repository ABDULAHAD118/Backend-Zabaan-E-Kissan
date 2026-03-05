"""
App package initializer.
Re-exports the FastAPI `app` instance for ASGI servers.
"""
from fastapi import FastAPI
# Import the FastAPI instance from the production entry point
from .main import app
__all__ = ["app", "get_app", "__version__"]
__version__ = "1.0.0"
def get_app() -> FastAPI:
    """Return the FastAPI application instance."""
    return app
