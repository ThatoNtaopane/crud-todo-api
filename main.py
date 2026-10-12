"""FlyRank Internship · Backend Track · Week 2 · Assignment A4
Auth · Login & protect
Stage 0: Setup server and Supabase client
"""

import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase_client import supabase_client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_api")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-id.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(
    title="FlyRank Auth API",
    description="Secure Authentication & Protected Routes with Supabase Auth & FastAPI",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Server running and connected to Supabase at %s on port %d", SUPABASE_URL, PORT)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "FlyRank Auth API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on port %d...", PORT)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
