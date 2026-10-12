"""AI-Generated Implementation (Initial Prompt)
Quarantined in ai-version/ for Stage 7 code review.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Auth API")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

security = HTTPBearer()

class Credentials(BaseModel):
    email: EmailStr
    password: str

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return resp.json()

@app.post("/auth/signup", status_code=201)
async def signup(creds: Credentials):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SUPABASE_URL}/auth/v1/signup", json=creds.dict(), headers=headers)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail="Signup failed")
        return resp.json()

@app.post("/auth/login")
async def login(creds: Credentials):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json=creds.dict(), headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        return resp.json()

@app.post("/auth/logout", status_code=204)
async def logout(user: dict = Depends(verify_jwt)):
    return None

@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile")
def profile(user: dict = Depends(verify_jwt)):
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "created_at": user.get("created_at")
    }
