"""
Application-level configuration.
All settings are read from environment variables (with sensible defaults).
"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# ── Paths ─────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent          # src/app/
MODEL_PATH = APP_DIR / "model" / "disease_detection_model.keras"
DISEASE_INFO_PATH = APP_DIR / "data" / "disease_info.json"
# ── Server ─────────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
# ── CORS ───────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOW_ORIGINS", "*")
ALLOW_ORIGINS: list[str] = (
    ["*"] if _raw_origins == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)
# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGODB_CONNECTION_STRING: str = os.getenv("MONGODB_CONNECTION_STRING", "")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "crop_prices_db")
MONGO_SERVER_SELECTION_TIMEOUT_MS: int = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000"))
MONGO_SOCKET_TIMEOUT_MS: int = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "10000"))
MONGO_CONNECT_TIMEOUT_MS: int = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))
# ── OpenAI ─────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
WHISPER_DEFAULT_LANGUAGE: str = os.getenv("WHISPER_DEFAULT_LANGUAGE", "ur")
# ── Disease Detection ──────────────────────────────────────────────────────────
IMG_SIZE: tuple[int, int] = (224, 224)
CLASS_NAMES: list[str] = [
    "Corn_Common_Rust", "Corn_Gray_Leaf_Spot", "Corn_Healthy", "Corn_Northern_Leaf_Blight",
    "Potato_Early_Blight", "Potato_Healthy", "Potato_Late_Blight",
    "Rice_Brown_Spot", "Rice_Healthy", "Rice_Leaf_Blast", "Rice_Neck_Blast",
    "Sugarcane_Bacterial_Blight", "Sugarcane_Healthy", "Sugarcane_Red_Rot",
    "Wheat_Brown_rust", "Wheat_Healthy", "Wheat_Yellow_Rust",
]
