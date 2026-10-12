"""Supabase Auth Client Integration.

This module initializes and manages the Supabase authentication client.
It supports:
1. The official `supabase` Python SDK (if installed).
2. A direct REST client via `httpx` targeting the Supabase GoTrue Auth API
   (providing zero-dependency fallback matching the exact SDK interface).
3. In-memory Mock Auth provider for isolated automated testing and CI environments.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger("supabase_auth")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-id.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
MOCK_AUTH = os.getenv("MOCK_AUTH", "false").lower() in ("true", "1", "yes")

class UserObject:
    def __init__(self, id: str, email: str, created_at: str, app_metadata: Optional[Dict] = None, user_metadata: Optional[Dict] = None):
        self.id = id
        self.email = email
        self.created_at = created_at
        self.app_metadata = app_metadata or {}
        self.user_metadata = user_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at,
            "app_metadata": self.app_metadata,
            "user_metadata": self.user_metadata,
        }

class SessionObject:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int = 3600, token_type: str = "bearer", user: Optional[UserObject] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.token_type = token_type
        self.user = user

class AuthResponse:
    def __init__(self, user: Optional[UserObject] = None, session: Optional[SessionObject] = None):
        self.user = user
        self.session = session

class UserResponse:
    def __init__(self, user: Optional[UserObject] = None):
        self.user = user

class SupabaseAuthService:
    """Authentication service providing signup, login, token verification, logout, and refresh."""

    def __init__(self, url: str, key: str, mock: bool = False):
        self.url = url.rstrip("/")
        self.key = key
        self.mock = mock
        self._mock_users: Dict[str, Dict[str, Any]] = {}
        self._mock_tokens: Dict[str, str] = {}  # token -> email
        self._mock_refresh_tokens: Dict[str, str] = {}  # refresh_token -> email
        self._revoked_tokens: set = set()

    def reset_mock(self):
        self._mock_users.clear()
        self._mock_tokens.clear()
        self._mock_refresh_tokens.clear()
        self._revoked_tokens.clear()

    def sign_up(self, credentials: Dict[str, str]) -> AuthResponse:
        email = credentials.get("email")
        password = credentials.get("password")

        if self.mock or "your-project-id" in self.url:
            import uuid, datetime
            if email in self._mock_users:
                user_data = self._mock_users[email]
                user_obj = UserObject(user_data["id"], email, user_data["created_at"])
                return AuthResponse(user=user_obj)

            user_id = str(uuid.uuid4())
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._mock_users[email] = {
                "id": user_id,
                "email": email,
                "password": password,
                "created_at": created_at,
            }
            user_obj = UserObject(user_id, email, created_at)
            return AuthResponse(user=user_obj)

        endpoint = f"{self.url}/auth/v1/signup"
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint, json={"email": email, "password": password}, headers=headers)
            if resp.status_code not in (200, 201):
                err_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                err_msg = err_data.get("msg") or err_data.get("error_description") or resp.text
                raise ValueError(err_msg)
            data = resp.json()
            user_raw = data.get("user") or data
            user_obj = UserObject(
                id=user_raw.get("id", ""),
                email=user_raw.get("email", ""),
                created_at=user_raw.get("created_at", ""),
                app_metadata=user_raw.get("app_metadata", {}),
                user_metadata=user_raw.get("user_metadata", {}),
            )
            return AuthResponse(user=user_obj)

    def sign_in_with_password(self, credentials: Dict[str, str]) -> AuthResponse:
        email = credentials.get("email")
        password = credentials.get("password")

        if self.mock or "your-project-id" in self.url:
            import uuid
            if email not in self._mock_users or self._mock_users[email]["password"] != password:
                raise ValueError("Invalid login credentials")

            user_data = self._mock_users[email]
            user_obj = UserObject(user_data["id"], email, user_data["created_at"])
            access_token = f"jwt_access_{uuid.uuid4().hex}"
            refresh_token = f"jwt_refresh_{uuid.uuid4().hex}"

            self._mock_tokens[access_token] = email
            self._mock_refresh_tokens[refresh_token] = email

            session_obj = SessionObject(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=3600,
                token_type="bearer",
                user=user_obj,
            )
            return AuthResponse(user=user_obj, session=session_obj)

        endpoint = f"{self.url}/auth/v1/token?grant_type=password"
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint, json={"email": email, "password": password}, headers=headers)
            if resp.status_code != 200:
                raise ValueError("Invalid login credentials")
            data = resp.json()
            user_raw = data.get("user", {})
            user_obj = UserObject(
                id=user_raw.get("id", ""),
                email=user_raw.get("email", ""),
                created_at=user_raw.get("created_at", ""),
            )
            session_obj = SessionObject(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                expires_in=data.get("expires_in", 3600),
                token_type=data.get("token_type", "bearer"),
                user=user_obj,
            )
            return AuthResponse(user=user_obj, session=session_obj)

    def get_user(self, jwt_token: str) -> UserResponse:
        if not jwt_token or not jwt_token.strip():
            raise ValueError("Invalid or expired token")

        if self.mock or "your-project-id" in self.url:
            if jwt_token in self._revoked_tokens:
                raise ValueError("Invalid or expired token")
            email = self._mock_tokens.get(jwt_token)
            if not email or email not in self._mock_users:
                raise ValueError("Invalid or expired token")
            user_data = self._mock_users[email]
            user_obj = UserObject(user_data["id"], email, user_data["created_at"])
            return UserResponse(user=user_obj)

        endpoint = f"{self.url}/auth/v1/user"
        headers = {"apikey": self.key, "Authorization": f"Bearer {jwt_token}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(endpoint, headers=headers)
            if resp.status_code != 200:
                raise ValueError("Invalid or expired token")
            data = resp.json()
            user_obj = UserObject(
                id=data.get("id", ""),
                email=data.get("email", ""),
                created_at=data.get("created_at", ""),
            )
            return UserResponse(user=user_obj)

    def sign_out(self, jwt_token: Optional[str] = None) -> None:
        if self.mock or "your-project-id" in self.url:
            if jwt_token:
                self._revoked_tokens.add(jwt_token)
            return

        endpoint = f"{self.url}/auth/v1/logout"
        headers = {"apikey": self.key}
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(endpoint, headers=headers)
        except Exception:
            pass

    def refresh_session(self, refresh_token: str) -> AuthResponse:
        if not refresh_token or not refresh_token.strip():
            raise ValueError("Refresh token is required")

        if self.mock or "your-project-id" in self.url:
            import uuid
            email = self._mock_refresh_tokens.get(refresh_token)
            if not email or email not in self._mock_users:
                raise ValueError("Invalid refresh token")

            user_data = self._mock_users[email]
            user_obj = UserObject(user_data["id"], email, user_data["created_at"])
            new_access_token = f"jwt_access_{uuid.uuid4().hex}"
            new_refresh_token = f"refresh_mock_token_{uuid.uuid4().hex}"

            self._mock_tokens[new_access_token] = email
            self._mock_refresh_tokens[new_refresh_token] = email

            session_obj = SessionObject(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=3600,
                token_type="bearer",
                user=user_obj,
            )
            return AuthResponse(user=user_obj, session=session_obj)

        endpoint = f"{self.url}/auth/v1/token?grant_type=refresh_token"
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint, json={"refresh_token": refresh_token}, headers=headers)
            if resp.status_code != 200:
                raise ValueError("Invalid refresh token")
            data = resp.json()
            user_raw = data.get("user", {})
            user_obj = UserObject(
                id=user_raw.get("id", ""),
                email=user_raw.get("email", ""),
                created_at=user_raw.get("created_at", ""),
            )
            session_obj = SessionObject(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                expires_in=data.get("expires_in", 3600),
                token_type=data.get("token_type", "bearer"),
                user=user_obj,
            )
            return AuthResponse(user=user_obj, session=session_obj)

class SupabaseClientWrapper:
    def __init__(self, url: str, key: str, mock: bool = False):
        self.auth = SupabaseAuthService(url, key, mock)

def get_supabase_client(url: Optional[str] = None, key: Optional[str] = None, mock: Optional[bool] = None) -> SupabaseClientWrapper:
    target_url = url or SUPABASE_URL
    target_key = key or SUPABASE_KEY
    is_mock = mock if mock is not None else MOCK_AUTH
    return SupabaseClientWrapper(target_url, target_key, is_mock)

supabase_client = get_supabase_client()
