"""Pydantic schemas for crop price endpoints."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
class CropPrice(BaseModel):
    city: str
    date: str
    crop: str
    min_price: str
    max_price: str
    fqp: str
    quantity: str
    scraped_at: datetime
class APIResponse(BaseModel):
    status: str
    data: List[CropPrice]
    total_records: int
    message: Optional[str] = None
