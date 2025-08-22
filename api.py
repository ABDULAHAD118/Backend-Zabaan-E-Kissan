from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API responses
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

class CropPriceAPI:
    def __init__(self, connection_string="mongodb+srv://abdulahadhussain60:burewala123@cluster0.ea9ayds.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", database_name="crop_prices_db"):
        """Initialize MongoDB connection for API"""
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db.crop_prices

            # Test connection
            self.client.admin.command('ping')
            logger.info("API successfully connected to MongoDB")

        except ConnectionFailure:
            logger.error("API failed to connect to MongoDB")
            raise

    def get_all_cities(self):
        """Get list of all available cities"""
        try:
            cities = self.collection.distinct("city")
            return sorted(cities)
        except Exception as e:
            logger.error(f"Error fetching cities: {e}")
            return []

    def get_all_crops(self, city: Optional[str] = None):
        """Get list of all available crops, optionally filtered by city"""
        try:
            filter_query = {"city": city} if city else {}
            crops = self.collection.distinct("crop", filter_query)
            return sorted(crops)
        except Exception as e:
            logger.error(f"Error fetching crops: {e}")
            return []

    def get_crop_prices(self,
                        city: Optional[str] = None,
                        crop: Optional[str] = None,
                        date: Optional[str] = None,
                        limit: int = 100,
                        skip: int = 0):
        """Get crop prices with optional filters"""
        try:
            # Build query filter
            filter_query = {}
            if city:
                filter_query["city"] = {"$regex": city, "$options": "i"}  # Case-insensitive search
            if crop:
                filter_query["crop"] = {"$regex": crop, "$options": "i"}  # Case-insensitive search
            if date:
                filter_query["date"] = date

            # Execute query with pagination
            cursor = self.collection.find(filter_query).skip(skip).limit(limit).sort("scraped_at", -1)
            results = list(cursor)

            # Get total count for pagination info
            total_count = self.collection.count_documents(filter_query)

            return results, total_count

        except Exception as e:
            logger.error(f"Error fetching crop prices: {e}")
            return [], 0

    def get_latest_prices(self, city: Optional[str] = None, limit: int = 50):
        """Get latest crop prices"""
        try:
            filter_query = {}
            if city:
                filter_query["city"] = {"$regex": city, "$options": "i"}

            # Get latest prices by finding the most recent scraped_at date
            cursor = self.collection.find(filter_query).sort("scraped_at", -1).limit(limit)
            results = list(cursor)

            return results, len(results)

        except Exception as e:
            logger.error(f"Error fetching latest prices: {e}")
            return [], 0

    def get_price_comparison(self, crop: str, cities: List[str]):
        """Compare prices of a specific crop across multiple cities"""
        try:
            filter_query = {
                "crop": {"$regex": crop, "$options": "i"},
                "city": {"$in": cities}
            }

            cursor = self.collection.find(filter_query).sort("scraped_at", -1)
            results = list(cursor)

            return results, len(results)

        except Exception as e:
            logger.error(f"Error fetching price comparison: {e}")
            return [], 0

# Initialize FastAPI app
app = FastAPI(
    title="Crop Prices API",
    description="API for accessing crop price data from Pakistan Agricultural Marketing Information Service",
    version="1.0.0"
)

# Initialize database connection
try:
    db_api = CropPriceAPI()
except Exception as e:
    logger.error(f"Failed to initialize API database connection: {e}")
    db_api = None

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Crop Prices API",
        "version": "1.0.0",
        "endpoints": {
            "/cities": "Get all available cities",
            "/crops": "Get all available crops",
            "/prices": "Get crop prices with filters",
            "/latest": "Get latest crop prices",
            "/compare": "Compare crop prices across cities"
        }
    }

@app.get("/cities")
async def get_cities():
    """Get all available cities"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cities = db_api.get_all_cities()
    return {
        "status": "success",
        "data": cities,
        "total_cities": len(cities)
    }

@app.get("/crops")
async def get_crops(city: Optional[str] = Query(None, description="Filter crops by city")):
    """Get all available crops, optionally filtered by city"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    crops = db_api.get_all_crops(city)
    return {
        "status": "success",
        "data": crops,
        "total_crops": len(crops),
        "filtered_by_city": city
    }

@app.get("/prices")
async def get_prices(
        city: Optional[str] = Query(None, description="Filter by city name"),
        crop: Optional[str] = Query(None, description="Filter by crop name"),
        date: Optional[str] = Query(None, description="Filter by specific date"),
        limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
        skip: int = Query(0, ge=0, description="Number of records to skip")
):
    """Get crop prices with optional filters"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    results, total_count = db_api.get_crop_prices(city, crop, date, limit, skip)

    # Convert ObjectId to string for JSON serialization
    for result in results:
        result['_id'] = str(result['_id'])

    return {
        "status": "success",
        "data": results,
        "total_records": total_count,
        "returned_records": len(results),
        "filters": {
            "city": city,
            "crop": crop,
            "date": date
        },
        "pagination": {
            "limit": limit,
            "skip": skip
        }
    }

@app.get("/latest")
async def get_latest_prices(
        city: Optional[str] = Query(None, description="Filter by city name"),
        limit: int = Query(50, ge=1, le=500, description="Number of records to return")
):
    """Get latest crop prices"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    results, total_count = db_api.get_latest_prices(city, limit)

    # Convert ObjectId to string for JSON serialization
    for result in results:
        result['_id'] = str(result['_id'])

    return {
        "status": "success",
        "data": results,
        "total_records": total_count,
        "filters": {
            "city": city
        }
    }

@app.get("/compare")
async def compare_prices(
        crop: str = Query(..., description="Crop name to compare"),
        cities: str = Query(..., description="Comma-separated list of cities")
):
    """Compare prices of a specific crop across multiple cities"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    city_list = [city.strip() for city in cities.split(',')]

    if len(city_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 cities required for comparison")

    results, total_count = db_api.get_price_comparison(crop, city_list)

    # Convert ObjectId to string for JSON serialization
    for result in results:
        result['_id'] = str(result['_id'])

    return {
        "status": "success",
        "data": results,
        "total_records": total_count,
        "comparison": {
            "crop": crop,
            "cities": city_list
        }
    }

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        total_records = db_api.collection.count_documents({})
        total_cities = len(db_api.get_all_cities())
        total_crops = len(db_api.get_all_crops())

        # Get latest update time
        latest_record = db_api.collection.find().sort("scraped_at", -1).limit(1)
        latest_update = None
        for record in latest_record:
            latest_update = record.get('scraped_at')
            break

        return {
            "status": "success",
            "statistics": {
                "total_records": total_records,
                "total_cities": total_cities,
                "total_crops": total_crops,
                "latest_update": latest_update
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)