"""
Production FastAPI application factory.
Run with:
    uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core import config
from .dependencies import set_db, set_ml_model
from .routers import chatbot, crop_prices, disease, transcription
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)
# ── Lifespan: start-up & shut-down ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Start-up ───────────────────────────────────────────────────────────────
    # 1. MongoDB
    try:
        from .services.crop_price_service import CropPriceService
        db = CropPriceService()
        set_db(db)
    except Exception as exc:
        logger.error("⚠️  MongoDB unavailable at startup: %s", exc)
    # 2. ML Model
    try:
        from .services.disease_service import load_model
        model = load_model()
        set_ml_model(model)
    except Exception as exc:
        logger.error("⚠️  ML model could not be loaded: %s", exc)
    logger.info("🚀 Application startup complete")
    yield
    # ── Shut-down ──────────────────────────────────────────────────────────────
    from .dependencies import _db_instance
    if _db_instance and hasattr(_db_instance, "close"):
        _db_instance.close()
    set_ml_model(None)
    logger.info("🛑 Application shutdown complete")
# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    application = FastAPI(
        title="AgriSmart API",
        description=(
            "Unified API for crop price data, plant disease detection, "
            "agricultural chatbot, and audio transcription."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Routers
    application.include_router(crop_prices.router)
    application.include_router(disease.router)
    application.include_router(chatbot.router)
    application.include_router(transcription.router)
    # ── General endpoints ──────────────────────────────────────────────────────
    @application.get("/", tags=["General"])
    async def root() -> Dict[str, Any]:
        return {
            "service": "AgriSmart API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "endpoints": {
                "crop_prices": {
                    "cities":  "GET  /crop/cities",
                    "crops":   "GET  /crop/crops",
                    "prices":  "GET  /crop/prices",
                    "latest":  "GET  /crop/latest",
                    "compare": "GET  /crop/compare",
                    "stats":   "GET  /crop/stats",
                },
                "disease_detection": {
                    "predict": "POST /disease/predict",
                    "classes": "GET  /disease/classes",
                },
                "chatbot": {
                    "chat":          "WS   /chat/{thread_id}",
                    "analyze_field": "GET  /chat/analyze-field",
                },
                "transcription": {
                    "transcribe": "POST /transcribe",
                },
            },
        }
    @application.get("/health", tags=["General"])
    async def health() -> Dict[str, Any]:
        from .dependencies import _db_instance, _ml_model
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "database": "connected" if _db_instance is not None else "unavailable",
                "ml_model": "loaded" if _ml_model is not None else "unavailable",
            },
        }
    @application.get("/ready", tags=["General"])
    async def readiness() -> Dict[str, Any]:
        from .dependencies import _db_instance
        try:
            if _db_instance is None:
                raise RuntimeError("DB not initialized")
            _db_instance.client.admin.command("ping")
            return {"status": "ready"}
        except Exception as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=f"Not ready: {exc}")
    return application
app = create_app()
