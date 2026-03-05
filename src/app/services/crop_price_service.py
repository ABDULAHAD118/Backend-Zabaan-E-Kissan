"""
MongoDB data-access layer for crop prices.
Encapsulates all database queries and connection management.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from ..core import config
logger = logging.getLogger(__name__)
class CropPriceService:
    """Manages MongoDB connection and all crop-price queries."""
    def __init__(self) -> None:
        if not config.MONGODB_CONNECTION_STRING:
            raise ValueError(
                "MONGODB_CONNECTION_STRING environment variable is not set."
            )
        try:
            self.client = MongoClient(
                config.MONGODB_CONNECTION_STRING,
                serverSelectionTimeoutMS=config.MONGO_SERVER_SELECTION_TIMEOUT_MS,
                socketTimeoutMS=config.MONGO_SOCKET_TIMEOUT_MS,
                connectTimeoutMS=config.MONGO_CONNECT_TIMEOUT_MS,
                retryWrites=True,
                uuidRepresentation="standard",
                tz_aware=True,
            )
            self.db = self.client[config.MONGODB_DB_NAME]
            self.collection = self.db.crop_prices
            self.chat_history_collection = self.db.chat_history
            self.client.admin.command("ping")
            logger.info("✅ Connected to MongoDB (%s)", config.MONGODB_DB_NAME)
            self._create_indexes()
        except ConnectionFailure:
            logger.error("❌ Failed to connect to MongoDB")
            raise
    def close(self) -> None:
        """Gracefully close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("🛑 MongoDB client closed")
    # ── Index management ───────────────────────────────────────────────────────
    def _create_indexes(self) -> None:
        try:
            for field in ("city", "crop", "date", "scraped_at"):
                self.collection.create_index(field)
            for field in ("thread_id", "timestamp"):
                self.chat_history_collection.create_index(field)
            logger.info("✅ MongoDB indexes ensured")
        except Exception as exc:
            logger.warning("Could not create indexes: %s", exc)
    # ── Query helpers ──────────────────────────────────────────────────────────
    def get_all_cities(self) -> List[str]:
        try:
            return sorted(self.collection.distinct("city"))
        except Exception as exc:
            logger.error("Error fetching cities: %s", exc)
            return []
    def get_all_crops(self, city: Optional[str] = None) -> List[str]:
        try:
            query = {"city": city} if city else {}
            return sorted(self.collection.distinct("crop", query))
        except Exception as exc:
            logger.error("Error fetching crops: %s", exc)
            return []
    def get_crop_prices(
        self,
        city: Optional[str] = None,
        crop: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[list, int]:
        try:
            query: dict = {
                "min_price": {"$nin": ["", "-", None]},
                "max_price": {"$nin": ["", "-", None]},
            }
            if city:
                query["city"] = city.strip()
            if crop:
                query["crop"] = crop.strip()
            if date:
                query["date"] = date
            cursor = self.collection.find(query).skip(skip).limit(limit).sort("scraped_at", -1)
            total = self.collection.count_documents(query)
            return list(cursor), total
        except Exception as exc:
            logger.error("Error fetching crop prices: %s", exc)
            return [], 0
    def get_latest_prices(
        self, city: Optional[str] = None, limit: int = 50
    ) -> Tuple[list, int]:
        try:
            query: dict = {}
            if city:
                query["city"] = {"$regex": city, "$options": "i"}
            results = list(
                self.collection.find(query).sort("scraped_at", -1).limit(limit)
            )
            return results, len(results)
        except Exception as exc:
            logger.error("Error fetching latest prices: %s", exc)
            return [], 0
    def get_price_comparison(
        self, crop: str, cities: List[str]
    ) -> Tuple[list, int]:
        try:
            query = {
                "crop": {"$regex": crop, "$options": "i"},
                "city": {"$in": cities},
            }
            results = list(self.collection.find(query).sort("scraped_at", -1))
            return results, len(results)
        except Exception as exc:
            logger.error("Error fetching price comparison: %s", exc)
            return [], 0
    def get_stats(self) -> dict:
        total_records = self.collection.count_documents({})
        total_cities = len(self.get_all_cities())
        total_crops = len(self.get_all_crops())
        latest = self.collection.find_one(sort=[("scraped_at", -1)])
        latest_update = latest.get("scraped_at") if latest else None
        return {
            "total_records": total_records,
            "total_cities": total_cities,
            "total_crops": total_crops,
            "latest_update": latest_update,
        }
    # ── Chat history ───────────────────────────────────────────────────────────
    def save_chat_message(self, thread_id: str, sender: str, message: str) -> None:
        try:
            self.chat_history_collection.insert_one(
                {
                    "thread_id": thread_id,
                    "sender": sender,
                    "message": message,
                    "timestamp": datetime.utcnow(),
                }
            )
        except Exception as exc:
            logger.error("Error saving chat message: %s", exc)
    def get_chat_history(self, thread_id: str) -> list:
        try:
            return list(
                self.chat_history_collection.find({"thread_id": thread_id}).sort(
                    "timestamp", 1
                )
            )
        except Exception as exc:
            logger.error("Error fetching chat history: %s", exc)
            return []
