"""Pydantic schemas for disease detection endpoints."""
from pydantic import BaseModel
class PredictionItem(BaseModel):
    class_name: str
    confidence: float
class PredictionResponse(BaseModel):
    predicted_class: str
    confidence_percent: float
    is_healthy: bool
    status: str
    severity_range: str
    description: str
    description_ur: str
    recommended_action: str
    recommended_action_ur: str
    confidence_level: str          # "High" | "Moderate" | "Low"
    top_3_predictions: list[PredictionItem]
