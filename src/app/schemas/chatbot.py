"""Pydantic schemas for chatbot endpoints."""
from pydantic import BaseModel, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    language: Optional[str] = "urdu"

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v):
        if v is None:
            return "urdu"
        v = str(v).strip().lower()
        if v not in ("urdu", "english"):
            return "urdu"
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "گندم کی کاشت کا وقت؟",
                "language": "urdu"
            }
        }
    }
