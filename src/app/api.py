import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pydantic import BaseModel
from dotenv import load_dotenv

# ✅ Chatbot imports
from .chatbotWorkflow import chatbot, rs_analyzer
from langchain_core.messages import HumanMessage


# --------------------------
# Load environment variables
# --------------------------
load_dotenv()

# --------------------------
# Configure logging
# --------------------------

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


# --------------------------
# Pydantic models
# --------------------------
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


class ChatRequest(BaseModel):
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "گندم کی کاشت کا وقت؟"
            }
        }

class ChatResponse(BaseModel):
    response: str
    field_analysis: Optional[dict] = None


# --------------------------
# Database Layer
# --------------------------
class CropPriceAPI:
    def __init__(self, connection_string=None, database_name="crop_prices_db"):
        if connection_string is None:
            connection_string = os.environ.get("MONGODB_CONNECTION_STRING")
            if not connection_string:
                raise ValueError("MongoDB connection string not found. Please set MONGODB_CONNECTION_STRING.")

        try:
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")),
                socketTimeoutMS=int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "10000")),
                connectTimeoutMS=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000")),
                retryWrites=True,
                uuidRepresentation="standard",
                tz_aware=True,
            )
            db_name = os.getenv("MONGODB_DB_NAME", database_name)
            self.db = self.client[db_name]
            self.collection = self.db.crop_prices

            # Test connection
            self.client.admin.command("ping")
            logger.info("✅ Successfully connected to MongoDB")

            # Create indexes
            self.create_indexes()
        except ConnectionFailure:
            logger.error("❌ Failed to connect to MongoDB")
            raise

    def create_indexes(self):
        try:
            self.collection.create_index("city")
            self.collection.create_index("crop")
            self.collection.create_index("date")
            self.collection.create_index("scraped_at")
            logger.info("✅ Indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    def get_all_cities(self):
        try:
            return sorted(self.collection.distinct("city"))
        except Exception as e:
            logger.error(f"Error fetching cities: {e}")
            return []

    def get_all_crops(self, city: Optional[str] = None):
        try:
            filter_query = {"city": city} if city else {}
            return sorted(self.collection.distinct("crop", filter_query))
        except Exception as e:
            logger.error(f"Error fetching crops: {e}")
            return []

    def get_crop_prices(self, city=None, crop=None, date=None, limit=100, skip=0):
        try:
            filter_query = {}
            if city:
                filter_query["city"] = {"$regex": city, "$options": "i"}
            if crop:
                filter_query["crop"] = {"$regex": crop, "$options": "i"}
            if date:
                filter_query["date"] = date

            cursor = self.collection.find(filter_query).skip(skip).limit(limit).sort("scraped_at", -1)
            results = list(cursor)
            total_count = self.collection.count_documents(filter_query)
            return results, total_count
        except Exception as e:
            logger.error(f"Error fetching crop prices: {e}")
            return [], 0

    def get_latest_prices(self, city=None, limit=50):
        try:
            filter_query = {}
            if city:
                filter_query["city"] = {"$regex": city, "$options": "i"}

            cursor = self.collection.find(filter_query).sort("scraped_at", -1).limit(limit)
            results = list(cursor)
            return results, len(results)
        except Exception as e:
            logger.error(f"Error fetching latest prices: {e}")
            return [], 0

    def get_price_comparison(self, crop: str, cities: List[str]):
        try:
            filter_query = {"crop": {"$regex": crop, "$options": "i"}, "city": {"$in": cities}}
            cursor = self.collection.find(filter_query).sort("scraped_at", -1)
            results = list(cursor)
            return results, len(results)
        except Exception as e:
            logger.error(f"Error fetching price comparison: {e}")
            return [], 0


# --------------------------
# FastAPI App Initialization
# --------------------------
app = FastAPI(
    title="Crop Prices & Chatbot API",
    description="API for accessing crop price data and chatbot responses",
    version="1.0.0",
)

# CORS
allowed_origins = os.getenv("ALLOW_ORIGINS", "*")
origins = ["*"] if allowed_origins == "*" else [o.strip() for o in allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection
db_api: Optional[CropPriceAPI] = None


@app.on_event("startup")
async def on_startup():
    global db_api
    try:
        db_api = CropPriceAPI()
        logger.info("🚀 API startup complete")
    except Exception as e:
        logger.exception(f"Startup failed: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    global db_api
    try:
        if db_api and db_api.client:
            db_api.client.close()
            logger.info("🛑 MongoDB client closed")
    except Exception as e:
        logger.exception(f"Shutdown cleanup failed: {e}")


# --------------------------
# Routes
# --------------------------
@app.get("/health", response_model=Dict[str, Any])
async def health():
    return {"status": "ok", "service": "crop-prices-chatbot-api", "time": datetime.utcnow().isoformat()}


@app.get("/ready", response_model=Dict[str, Any])
async def readiness():
    try:
        if not db_api:
            raise RuntimeError("DB not initialized")
        db_api.client.admin.command("ping")
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")


@app.get("/", response_model=Dict[str, Any])
async def root():
    return {
        "message": "Crop Prices & Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/cities": "Get all available cities",
            "/crops": "Get all available crops",
            "/prices": "Get crop prices with filters",
            "/latest": "Get latest crop prices",
            "/compare": "Compare crop prices across cities",
            "/stats": "Get database statistics",
            "chat": "/chat/{thread_id}",
            "history": "/chat/{thread_id}/history",
            "analyze": "/analyze-field",
            "docs": "/docs1"
        },
    }


# ----- Crop Price Endpoints -----
@app.get("/cities")
async def get_cities():
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cities = db_api.get_all_cities()
    return {"status": "success", "data": cities, "total_cities": len(cities)}


@app.get("/crops")
async def get_crops(city: Optional[str] = Query(None, description="Filter crops by city")):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    crops = db_api.get_all_crops(city)
    return {"status": "success", "data": crops, "total_crops": len(crops), "filtered_by_city": city}


@app.get("/prices")
async def get_prices(city: Optional[str] = None, crop: Optional[str] = None, date: Optional[str] = None,
                     limit: int = Query(100, ge=1, le=1000), skip: int = Query(0, ge=0)):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    results, total_count = db_api.get_crop_prices(city, crop, date, limit, skip)
    for result in results:
        result["_id"] = str(result["_id"])
    return {
        "status": "success",
        "data": results,
        "total_records": total_count,
        "returned_records": len(results),
        "filters": {"city": city, "crop": crop, "date": date},
        "pagination": {"limit": limit, "skip": skip},
    }


@app.get("/latest")
async def get_latest_prices(city: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    results, total_count = db_api.get_latest_prices(city, limit)
    for result in results:
        result["_id"] = str(result["_id"])
    return {"status": "success", "data": results, "total_records": total_count, "filters": {"city": city}}


@app.get("/compare")
async def compare_prices(crop: str, cities: str):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    city_list = [city.strip() for city in cities.split(",")]
    if len(city_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 cities required for comparison")
    results, total_count = db_api.get_price_comparison(crop, city_list)
    for result in results:
        result["_id"] = str(result["_id"])
    return {"status": "success", "data": results, "total_records": total_count,
            "comparison": {"crop": crop, "cities": city_list}}


@app.get("/stats")
async def get_stats():
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        total_records = db_api.collection.count_documents({})
        total_cities = len(db_api.get_all_cities())
        total_crops = len(db_api.get_all_crops())
        latest_record = db_api.collection.find().sort("scraped_at", -1).limit(1)
        latest_update = None
        for record in latest_record:
            latest_update = record.get("scraped_at")
            break
        return {"status": "success", "statistics": {
            "total_records": total_records,
            "total_cities": total_cities,
            "total_crops": total_crops,
            "latest_update": latest_update,
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat/{thread_id}", response_model=ChatResponse)
async def chat(thread_id: str, chat_request: ChatRequest):
    try:
        result = chatbot.invoke(message=chat_request.query, thread_id=thread_id)
        return ChatResponse(response=result["response"], field_analysis=result.get("field_analysis"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{thread_id}/history")
async def get_history(thread_id: str):
    try:
        messages = chatbot.get_history(thread_id)
        return {"thread_id": thread_id, "message_count": len(messages), "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze-field")
async def analyze_field(lat: float, lon: float):
    if not (23 <= lat <= 37 and 60 <= lon <= 78):
        raise HTTPException(status_code=400, detail="Invalid Pakistan coordinates")
    try:
        return rs_analyzer.analyze_field(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    print("""
    ╔════════════════════════════════════╗
    ║  🌾 Zuban-e-Kisan API Started 🌾 ║
    ╚════════════════════════════════════╝
    📡 http://localhost:8000
    📖 http://localhost:8000/docs
    """)