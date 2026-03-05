"""
Plant disease detection service.
Handles model loading, image preprocessing, and inference.
"""
import io
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import numpy as np
from fastapi import HTTPException
from PIL import Image
from ..core import config
logger = logging.getLogger(__name__)
# ── Load disease metadata once at module import ────────────────────────────────
def _load_disease_info() -> Dict[str, dict]:
    try:
        with open(config.DISEASE_INFO_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("✅ Loaded disease info (%d entries)", len(data))
        return data
    except FileNotFoundError:
        logger.error("disease_info.json not found at %s", config.DISEASE_INFO_PATH)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in disease_info.json: %s", exc)
        return {}
DISEASE_INFO: Dict[str, dict] = _load_disease_info()
# ── Model loader ───────────────────────────────────────────────────────────────
def load_model():
    """Load and return the Keras disease detection model."""
    from tensorflow import keras  # lazy import to avoid slow startup if unused
    model_path = config.MODEL_PATH
    if not Path(model_path).exists():
        raise RuntimeError(f"Model file not found: {model_path}")
    logger.info("Loading model from %s ...", model_path)
    model = keras.models.load_model(model_path)
    logger.info("✅ Disease detection model loaded")
    return model
# ── Image utilities ────────────────────────────────────────────────────────────
def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes, resize to model input size, normalise to [0, 1],
    and add a batch dimension.
    Raises:
        HTTPException(400): if the bytes cannot be decoded as an image.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. Please upload a valid PNG/JPG image.",
        )
    img = img.resize(config.IMG_SIZE)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)
def confidence_label(confidence: float) -> str:
    """Map a raw confidence percentage to a human-readable label."""
    if confidence >= 85:
        return "High"
    if confidence >= 70:
        return "Moderate"
    return "Low"
# ── Inference ─────────────────────────────────────────────────────────────────
def run_inference(model, image_bytes: bytes) -> dict:
    """
    Run the disease detection model on raw image bytes and return a structured
    prediction result.
    Args:
        model:        Loaded Keras model instance.
        image_bytes:  Raw bytes of the uploaded image.
    Returns:
        dict matching the PredictionResponse schema fields.
    """
    img_array = preprocess_image(image_bytes)
    predictions: np.ndarray = model.predict(img_array, verbose=0)[0]  # shape (17,)
    predicted_idx = int(np.argmax(predictions))
    predicted_class = config.CLASS_NAMES[predicted_idx]
    confidence = float(predictions[predicted_idx]) * 100
    # Top-3 predictions
    top3_indices = np.argsort(predictions)[-3:][::-1]
    top3 = [
        {
            "class_name": config.CLASS_NAMES[i],
            "confidence": round(float(predictions[i]) * 100, 2),
        }
        for i in top3_indices
    ]
    info = DISEASE_INFO.get(predicted_class, {})
    return {
        "predicted_class": predicted_class,
        "confidence_percent": round(confidence, 2),
        "is_healthy": "Healthy" in predicted_class,
        "status": info.get("status", "Unknown"),
        "severity_range": info.get("severity_range", "Unknown"),
        "description": info.get("description", "N/A"),
        "description_ur": info.get("description_ur", "N/A"),
        "recommended_action": info.get("action", "Consult an agriculture expert"),
        "recommended_action_ur": info.get("action_ur", "زرعی ماہر سے مشورہ کریں"),
        "confidence_level": confidence_label(confidence),
        "top_3_predictions": top3,
    }
