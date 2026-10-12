"""FlyRank Internship · Backend Track · Week 2 · Assignment A4
Auth · Login & protect
Stage 2: Public route and unverified protected route
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Email and password are required"}
    )

class AuthCredentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    logger.info("Server running and connected to Supabase at %s on port %d", SUPABASE_URL, PORT)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "FlyRank Auth API"}

@app.post("/auth/signup", status_code=201, tags=["Authentication"])
def signup(creds: AuthCredentials):
    if not creds.email or not creds.email.strip() or not creds.password or not creds.password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        res = supabase_client.auth.sign_up({"email": creds.email.strip(), "password": creds.password.strip()})
        user = res.user
        return JSONResponse(
            status_code=201,
            content={
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
                "message": "User registered successfully"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/auth/login", status_code=200, tags=["Authentication"])
def login(creds: AuthCredentials):
    if not creds.email or not creds.email.strip() or not creds.password or not creds.password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        res = supabase_client.auth.sign_in_with_password({"email": creds.email.strip(), "password": creds.password.strip()})
        session = res.session
        user = res.user
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": session.token_type,
            "expires_in": session.expires_in,
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})

# Stage 2: Public route
@app.get("/public/info", tags=["Public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}

# Stage 2: Unverified protected route (checks presence of Authorization header)
@app.get("/protected/profile", tags=["Protected"])
def get_profile_unverified(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Access token required"})
    
    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        return JSONResponse(status_code=401, content={"error": "Access token required"})
    
    # In Stage 2, checking token presence before verification is hooked up
    return {"message": "Token presented (verification not enabled yet)", "raw_token_prefix": token[:10]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
