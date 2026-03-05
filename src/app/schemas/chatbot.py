"""Pydantic schemas for chatbot endpoints."""
from pydantic import BaseModel
class ChatRequest(BaseModel):
    query: str
    model_config = {
        "json_schema_extra": {
            "example": {"query": "گندم کی کاشت کا وقت؟"}
        }
    }
