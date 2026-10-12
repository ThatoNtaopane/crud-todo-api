"""FlyRank Internship · Backend Track · Week 2 · Assignment A4
Auth · Login & protect
Complete Implementation: Core Stages 0-5 + Stretch Goals (403 Forbidden, Refresh Token, Rate Limiting)
"""

import os
import time
import logging
from typing import Optional, Dict
from collections import defaultdict
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
ADMIN_EMAILS = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "admin@example.com,thatontaopane@gmail.com").split(",") if e.strip()]

# In-memory Rate Limiting Tracker for Login Brute Force Protection
LOGIN_ATTEMPTS: Dict[str, list] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds

app = FastAPI(
    title="FlyRank Auth API",
    description="""
## Secure Authentication & Authorization API
Built for the **FlyRank Backend Track (Week 2, Assignment A4)**.

### Architectural Highlights
* **Identity Provider (IdP)**: Supabase Auth handles password hashing, credentials storage, and JWT signing.
* **Stateless Verification**: Bearer JWT tokens verified on protected endpoints.
* **Role-Based Authorization (403 Forbidden)**: Clear separation between 401 Unauthorized and 403 Forbidden.
* **Token Rotation**: Refresh token exchange via `POST /auth/refresh`.
* **Brute-Force Defense**: In-memory rate limiting returning `429 Too Many Requests`.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System", "description": "Operational health and service discovery"},
        {"name": "Authentication", "description": "User registration, token issuance, session refresh, and logout"},
        {"name": "Public", "description": "Unprotected open endpoints accessible to anyone"},
        {"name": "Protected", "description": "Guarded endpoints requiring valid Bearer JWT authentication"},
        {"name": "Administration", "description": "Privileged routes requiring authenticated admin role (403 check)"}
    ]
)

# HTTPBearer Security Scheme for Swagger UI padlock
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

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None

# Reusable authentication dependency (FastAPI guard)
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
        return {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
            "token": token,
            "is_admin": user.email.lower() in ADMIN_EMAILS
        }
    except CustomAuthException:
        raise
    except Exception:
        raise CustomAuthException(status_code=401, detail="Invalid or expired token")

# Admin role dependency (Demonstrates 403 Forbidden)
def require_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        # 401 = "I don't know who you are"
        # 403 = "I know exactly who you are, and you are not allowed"
        raise CustomAuthException(status_code=403, detail="Forbidden: Admin privileges required")
    return current_user

@app.on_event("startup")
async def startup_event():
    logger.info("Server running and connected to Supabase at %s on port %d", SUPABASE_URL, PORT)

@app.get("/", tags=["System"], summary="Root Service Information")
def get_root():
    return {
        "name": "FlyRank Auth API",
        "version": "2.0.0",
        "documentation": "/docs",
        "endpoints": {
            "signup": "/auth/signup",
            "login": "/auth/login",
            "logout": "/auth/logout",
            "refresh": "/auth/refresh",
            "public_info": "/public/info",
            "profile": "/protected/profile",
            "dashboard": "/protected/dashboard",
            "admin": "/protected/admin"
        }
    }

@app.get("/health", tags=["System"], summary="Health Check")
def health_check():
    return {"status": "ok", "service": "FlyRank Auth API"}

@app.post("/auth/signup", status_code=201, tags=["Authentication"], summary="Register New User Account")
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

@app.post("/auth/login", status_code=200, tags=["Authentication"], summary="Authenticate and Return JWT Session")
def login(creds: AuthCredentials, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    # Rate limiting: filter out attempts older than window
    LOGIN_ATTEMPTS[client_ip] = [t for t in LOGIN_ATTEMPTS[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(LOGIN_ATTEMPTS[client_ip]) >= MAX_LOGIN_ATTEMPTS:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many failed login attempts. Please try again after 5 minutes."}
        )

    if not creds.email or not creds.email.strip() or not creds.password or not creds.password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        res = supabase_client.auth.sign_in_with_password({"email": creds.email.strip(), "password": creds.password.strip()})
        session = res.session
        user = res.user

        # Clear failed attempt history upon successful login
        LOGIN_ATTEMPTS[client_ip].clear()

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
        # Record failed attempt for rate limiting
        LOGIN_ATTEMPTS[client_ip].append(now)
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})

@app.post("/auth/refresh", status_code=200, tags=["Authentication"], summary="Exchange Refresh Token for Fresh JWT")
def refresh_token_endpoint(payload: RefreshTokenRequest):
    if not payload.refresh_token or not payload.refresh_token.strip():
        return JSONResponse(status_code=400, content={"error": "Refresh token is required"})

    try:
        res = supabase_client.auth.refresh_session(payload.refresh_token.strip())
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
        return JSONResponse(status_code=401, content={"error": "Invalid or expired refresh token"})

@app.post("/auth/logout", status_code=204, tags=["Authentication"], summary="End User Session")
def logout(current_user: dict = Depends(get_current_user)):
    try:
        supabase_client.auth.sign_out(current_user.get("token"))
    except Exception:
        pass
    return Response(status_code=204)

@app.get("/public/info", tags=["Public"], summary="Public Information Endpoint")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile", tags=["Protected"], summary="Get Authenticated User Profile")
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
            "access_level": "admin" if current_user.get("is_admin") else "standard"
        }
    }

@app.get("/protected/admin", tags=["Administration"], summary="Admin Only Restricted Area (403 Demo)")
def get_admin_data(admin_user: dict = Depends(require_admin_user)):
    return {
        "message": "Welcome, Administrator! You have accessed the protected admin realm.",
        "admin_email": admin_user["email"],
        "system_status": "All systems operational",
        "privileged_metrics": {
            "total_users_registered": 142,
            "active_jwt_sessions": 38,
            "security_alerts": 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
