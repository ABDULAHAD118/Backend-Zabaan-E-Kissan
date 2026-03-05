"""
FastAPI dependency providers.
Singleton instances (DB client, ML model) are stored as module-level
variables and injected via FastAPI's Depends() mechanism.
"""
from __future__ import annotations
import logging
from typing import Optional
from fastapi import HTTPException
logger = logging.getLogger(__name__)
# ── Singleton holders (populated during app lifespan) ─────────────────────────
_db_instance: Optional[object] = None
_ml_model: Optional[object] = None
# ── Setters called from lifespan ───────────────────────────────────────────────
def set_db(instance) -> None:
    global _db_instance
    _db_instance = instance
def set_ml_model(model) -> None:
    global _ml_model
    _ml_model = model
# ── FastAPI Depends providers ──────────────────────────────────────────────────
def get_db():
    """Return the active CropPriceService instance."""
    if _db_instance is None:
        raise HTTPException(status_code=503, detail="Database service is unavailable.")
    return _db_instance
def get_ml_model():
    """Return the loaded Keras model (may be None if loading failed)."""
    return _ml_model
