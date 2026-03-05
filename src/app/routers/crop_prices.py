"""
Crop prices router.
Exposes endpoints for cities, crops, price queries, and statistics.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_db
from ..services.crop_price_service import CropPriceService
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crop", tags=["Crop Prices"])
@router.get("/cities", summary="List all available cities")
async def get_cities(db: CropPriceService = Depends(get_db)):
    cities = db.get_all_cities()
    return {"status": "success", "data": cities, "total_cities": len(cities)}
@router.get("/crops", summary="List all available crops")
async def get_crops(
    city: Optional[str] = Query(None, description="Filter by city"),
    db: CropPriceService = Depends(get_db),
):
    crops = db.get_all_crops(city)
    return {
        "status": "success",
        "data": crops,
        "total_crops": len(crops),
        "filtered_by_city": city,
    }
@router.get("/prices", summary="Query crop prices with optional filters")
async def get_prices(
    city: Optional[str] = None,
    crop: Optional[str] = None,
    date: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=1000),
    db: CropPriceService = Depends(get_db),
):
    skip = (page - 1) * limit
    results, total = db.get_crop_prices(city, crop, date, limit, skip)
    for r in results:
        r["_id"] = str(r["_id"])
    total_pages = max(1, (total + limit - 1) // limit)
    return {
        "status": "success",
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_records": total,
            "returned_records": len(results),
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "filters": {"city": city, "crop": crop, "date": date},
    }
@router.get("/latest", summary="Get the most recent crop prices")
async def get_latest_prices(
    city: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: CropPriceService = Depends(get_db),
):
    results, total = db.get_latest_prices(city, limit)
    for r in results:
        r["_id"] = str(r["_id"])
    return {"status": "success", "data": results, "total_records": total, "filters": {"city": city}}
@router.get("/compare", summary="Compare a crop's price across multiple cities")
async def compare_prices(
    crop: str,
    cities: str = Query(..., description="Comma-separated city names (min 2)"),
    db: CropPriceService = Depends(get_db),
):
    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    if len(city_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 cities are required for comparison.")
    results, total = db.get_price_comparison(crop, city_list)
    for r in results:
        r["_id"] = str(r["_id"])
    return {
        "status": "success",
        "data": results,
        "total_records": total,
        "comparison": {"crop": crop, "cities": city_list},
    }
@router.get("/stats", summary="Database statistics")
async def get_stats(db: CropPriceService = Depends(get_db)):
    try:
        stats = db.get_stats()
        return {"status": "success", "statistics": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {exc}")
