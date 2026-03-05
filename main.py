"""
Root entry point.
Run with:
    python main.py
or directly with uvicorn:
    uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
"""
import uvicorn
from dotenv import load_dotenv
import os
load_dotenv()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("APP_ENV", "development").lower() == "development"
if __name__ == "__main__":
    print(f"Starting AgriSmart API on {HOST}:{PORT} (reload={RELOAD})")
    uvicorn.run(
        "src.app.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
    )
