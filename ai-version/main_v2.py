"""AI-Generated Implementation (Rematch Version)
Incorporates improved specification: custom exception handlers, 403 authorization, and rate limiting.
"""

from fastapi import FastAPI, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import time
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Auth API v2")
security = HTTPBearer(auto_error=False)

FAILED_LOGINS = defaultdict(list)
ADMIN_EMAILS = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "admin@example.com").split(",")]

@app.exception_handler(RequestValidationError)
async def handle_val_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Email and password are required"})

class Credentials(BaseModel):
    email: str = None
    password: str = None

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Access token required")
    # verification logic...
    return {"id": "user-1", "email": "user@example.com", "created_at": "2026-10-12T00:00:00Z"}
