"""FlyRank Internship · Backend Track · Week 2 · Assignment A4
Auth · Login & protect
Stage 5: Swagger UI documentation with bearer auth
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    description="Secure Authentication & Protected Routes with Supabase Auth, JWT Verification, and Swagger UI Bearer Lock.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System", "description": "Operational health and service discovery"},
        {"name": "Authentication", "description": "User lifecycle: signup, login, and session revocation"},
        {"name": "Public", "description": "Open public endpoints accessible without credentials"},
        {"name": "Protected", "description": "Guarded endpoints requiring valid Bearer JWT tokens"}
    ]
)

# Configure HTTPBearer scheme so Swagger UI shows the Authorize padlock
security = HTTPBearer(auto_error=False)

class CustomAuthException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

@app.exception_handler(CustomAuthException)
async def custom_auth_exception_handler(request: Request, exc: CustomAuthException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Email and password are required"}
    )

class AuthCredentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

# Reusable authentication dependency integrated with HTTPBearer
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials or not credentials.credentials:
        raise CustomAuthException(status_code=401, detail="Access token required")

    token = credentials.credentials.strip()
    if not token:
        raise CustomAuthException(status_code=401, detail="Access token required")

    try:
        user_res = supabase_client.auth.get_user(token)
        user = user_res.user
        if not user or not user.id:
            raise CustomAuthException(status_code=401, detail="Invalid or expired token")
        return {"id": user.id, "email": user.email, "created_at": user.created_at, "token": token}
    except CustomAuthException:
        raise
    except Exception:
        raise CustomAuthException(status_code=401, detail="Invalid or expired token")

@app.on_event("startup")
async def startup_event():
    logger.info("Server running and connected to Supabase at %s on port %d", SUPABASE_URL, PORT)

@app.get("/health", tags=["System"], summary="Health Check")
def health_check():
    return {"status": "ok", "service": "FlyRank Auth API"}

@app.post("/auth/signup", status_code=201, tags=["Authentication"], summary="Register New User")
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

@app.post("/auth/login", status_code=200, tags=["Authentication"], summary="Authenticate and Return JWT")
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

@app.post("/auth/logout", status_code=204, tags=["Authentication"], summary="End User Session")
def logout(current_user: dict = Depends(get_current_user)):
    try:
        supabase_client.auth.sign_out(current_user.get("token"))
    except Exception:
        pass
    return Response(status_code=204)

@app.get("/public/info", tags=["Public"], summary="Public Information")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile", tags=["Protected"], summary="Get User Profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "created_at": current_user["created_at"]
    }

@app.get("/protected/dashboard", tags=["Protected"], summary="Get User Dashboard")
def get_dashboard(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Welcome to your private dashboard, {current_user['email']}!",
        "user_id": current_user["id"],
        "stats": {
            "active_sessions": 1,
            "role": "authenticated",
            "access_level": "standard"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
