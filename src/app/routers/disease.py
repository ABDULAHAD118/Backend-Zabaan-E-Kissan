"""
Plant disease detection router.
POST /disease/predict  – Upload a leaf image for disease classification.
GET  /disease/classes  – List all supported disease class names.
"""
import logging
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from ..dependencies import get_ml_model
from ..services import disease_service
from ..schemas.disease import PredictionResponse
from ..core import config
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/disease", tags=["Disease Detection"])
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
@router.get("/classes", summary="List all supported disease class names")
async def get_classes():
    return {"total": len(config.CLASS_NAMES), "classes": config.CLASS_NAMES}
@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Detect plant disease from a leaf image",
    description=(
        "Upload a plant leaf image (JPEG / PNG / WebP) and receive a disease "
        "classification with confidence score, severity, and treatment recommendations."
    ),
)
async def predict(
    file: UploadFile = File(..., description="Plant leaf image (JPG or PNG)"),
    model=Depends(get_ml_model),
):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Disease detection model is not loaded yet. Please try again shortly.",
        )
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                "Please upload a JPEG, PNG, or WebP image."
            ),
        )
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    result = disease_service.run_inference(model, image_bytes)
    return PredictionResponse(**result)
