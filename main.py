import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Retrieve host and port from environment variables
# Note: os.getenv() returns a string, so we must cast the port to an integer.
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")

if __name__ == "__main__":
    print(f"Starting server... {type(HOST)} {PORT}")
    uvicorn.run(
        "src.app.api:app",
        host=HOST,
        port=int(PORT),
        reload=True
    )
