import os
import logging
import tempfile
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import json
import asyncio

# ✅ Chatbot imports
from .chatbotWorkflow import chatbot, rs_analyzer
from langchain_core.messages import HumanMessage


# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

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
            self.chat_history_collection = self.db.chat_history

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
            # Crop prices indexes
            self.collection.create_index("city")
            self.collection.create_index("crop")
            self.collection.create_index("date")
            self.collection.create_index("scraped_at")

            # Chat history indexes
            self.chat_history_collection.create_index("thread_id")
            self.chat_history_collection.create_index("timestamp")

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


    def get_crop_prices(self, city=None, crop=None, date=None, limit=20, skip=0):
        try:
            filter_query = {}
            if city:
                filter_query["city"] = city.strip()
            if crop:
                filter_query["crop"] = crop.strip()
            if date:
                filter_query["date"] = date
            filter_query["min_price"] = {"$nin": ["", "-", None]}
            filter_query["max_price"] = {"$nin": ["", "-", None]}

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

    def save_chat_message(self, thread_id: str, sender: str, message: str):
        try:
            doc = {
                "thread_id": thread_id,
                "sender": sender,
                "message": message,
                "timestamp": datetime.utcnow()
            }
            self.chat_history_collection.insert_one(doc)
            logger.info(f"Saved chat message for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error saving chat message for thread {thread_id}: {e}")

    def get_chat_history(self, thread_id: str):
        try:
            cursor = self.chat_history_collection.find({"thread_id": thread_id}).sort("timestamp", 1)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error fetching chat history for thread {thread_id}: {e}")
            return []



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
            "transcribe": "/chat/transcribe",
            "analyze": "/analyze-field",
            "docs": "/docs"
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
async def get_prices(
    city: Optional[str] = None,
    crop: Optional[str] = None,
    date: Optional[str] = None,
    page: int = Query(1, ge=1),  # new param
    limit: int = Query(20, ge=1, le=1000),
):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # Calculate skip from page
    skip = (page - 1) * limit

    results, total_count = db_api.get_crop_prices(city, crop, date, limit, skip)

    for result in results:
        result["_id"] = str(result["_id"])

    total_pages = (total_count + limit - 1) // limit  # ceiling division

    return {
        "status": "success",
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_records": total_count,
            "returned_records": len(results),
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "filters": {"city": city, "crop": crop, "date": date},
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


@app.post("/chat/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (M4A format supported)"),
    language: str = Form(default="ur", description="Language code (default: 'ur' for Urdu)")
):
    """
    Transcribe audio to text using OpenAI Whisper API.
    
    Accepts audio files in various formats (M4A, MP3, WAV, etc.) and returns transcribed text.
    Default language is Urdu ('ur').
    
    Returns:
        - transcript: Transcribed text (if successful)
        - text: Alternative field name for transcribed text
    """
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Read audio file content
        audio_content = await audio.read()
        
        # Save to temporary file (OpenAI API requires file-like object)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio.filename.split('.')[-1]}") as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe using OpenAI Whisper API
            with open(temp_file_path, "rb") as audio_file:
                # Whisper supports Urdu language code "ur" and many other languages
                # If language is specified, use it; otherwise let Whisper auto-detect
                transcription_params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "json"
                }
                # Only set language if explicitly provided and not empty
                if language and language.strip():
                    transcription_params["language"] = language.strip()
                
                transcript_response = client.audio.transcriptions.create(**transcription_params)
            
            # Extract transcript text
            transcript_text = transcript_response.text
            
            logger.info(f"✅ Successfully transcribed audio: {len(transcript_text)} characters, language: {language}")
            
            # Return in the format expected by the frontend
            # Supports both "transcript" and "text" fields for compatibility
            return {
                "transcript": transcript_text,
                "text": transcript_text
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@app.websocket("/chat/{thread_id}")
async def chat_socket(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    print(f"🧠 Client connected on thread {thread_id}")

    if not db_api:
        print(f"❌ DB API not available for thread {thread_id}")
        await websocket.close(code=1011, reason="Server error: DB not configured")
        return

    if not chatbot:
        print(f"❌ Chatbot not available for thread {thread_id}")
        await websocket.close(code=1011, reason="Server error: Chatbot not configured")
        return

    try:
        while True:
            # 1. Receive message from client
            message_data = await websocket.receive_text()
            data = json.loads(message_data)
            user_message = data.get("query", "")

            print(f"👤 User message ({thread_id}):", user_message)

            # 2. Save user message to DB
            db_api.save_chat_message(
                thread_id=thread_id,
                sender="user",
                message=user_message
            )

            full_response = ""

            # 3. Stream response from your *real* chatbot
            try:
                async for chunk in chatbot.stream(message=user_message, thread_id=thread_id):
                    print("chunk:" ,chunk)
                    if chunk:
                        full_response += chunk
                        # Send chunk to the client
                        await websocket.send_text(json.dumps({"response": chunk}))

            except Exception as e:
                logger.error(f"Chatbot streaming error for thread {thread_id}: {e}")
                await websocket.send_text(json.dumps({
                    "response": "Sorry, an error occurred while generating a response."
                }))

            # 4. Save the full AI response to DB
            if full_response.strip():
                db_api.save_chat_message(
                    thread_id=thread_id,
                    sender="ai",
                    message=full_response.strip()
                )

            # 5. Send the "done" signal
            await websocket.send_text(json.dumps({"done": True}))

    except WebSocketDisconnect:
        print(f"❌ Client disconnected from {thread_id}")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error for thread {thread_id}: {e}")
        try:
            # Try to close gracefully if anything unexpected happens
            await websocket.close(code=1011, reason=f"Unexpected server error")
        except:
            pass  # Connection might already be gone

@app.get("/chat/{thread_id}/history")
async def get_history(thread_id: str):
    if not db_api:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        messages = db_api.get_chat_history(thread_id)
        # Convert ObjectId to string for JSON serialization
        for message in messages:
            message["_id"] = str(message["_id"])
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
    print(f"""
    ╔════════════════════════════════════╗
    ║  🌾 Zuban-e-Kisan API Started 🌾 ║
    ╚════════════════════════════════════╝
    📡 http://{os.getenv("HOST")}:{os.getenv("PORT")}
    📖 http://{os.getenv("HOST")}:{os.getenv("PORT")}/docs
    """)