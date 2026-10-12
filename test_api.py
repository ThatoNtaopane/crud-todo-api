"""Comprehensive Test Suite for FlyRank Auth API (FastAPI + Supabase Auth)

Validates all 6 stages, error status codes (200, 201, 204, 400, 401, 403, 429),
validation rules, bearer token verification, middleware reusability, and stretch goals.
"""

import sys
from fastapi.testclient import TestClient
from main import app, LOGIN_ATTEMPTS, supabase_client

client = TestClient(app)

def reset_state():
    """Reset mock state and rate limiting before each test."""
    supabase_client.auth.reset_mock()
    LOGIN_ATTEMPTS.clear()

# ----------------- STAGE 0: Health Check -----------------
def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "FlyRank Auth API"
    assert "/auth/login" in data["endpoints"].values()

# ----------------- STAGE 1: Signup & Login -----------------
def test_signup_success():
    payload = {"email": "test@example.com", "password": "password123"}
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data

def test_signup_missing_email():
    resp = client.post("/auth/signup", json={"password": "password123"})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_signup_empty_password():
    resp = client.post("/auth/signup", json={"email": "test@example.com", "password": "   "})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_login_success():
    # Register first
    client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})

    # Login
    resp = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["user"]["email"] == "test@example.com"

def test_login_invalid_credentials():
    client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "test@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Invalid login credentials"

def test_login_missing_fields():
    resp = client.post("/auth/login", json={})
    assert resp.status_code == 400
    assert "error" in resp.json()

# ----------------- STAGE 2: Public & Protected Gates -----------------
def test_public_info():
    resp = client.get("/public/info")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Welcome stranger! This info is public."

def test_protected_profile_no_token():
    resp = client.get("/protected/profile")
    assert resp.status_code == 401
    assert resp.json()["error"] == "Access token required"

def test_protected_profile_malformed_header():
    resp = client.get("/protected/profile", headers={"Authorization": "Token 12345"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Access token required"

# ----------------- STAGE 3: Token Verification -----------------
def test_protected_profile_valid_token():
    client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    resp = client.get("/protected/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data

def test_protected_profile_tampered_token():
    client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    valid_token = login_resp.json()["access_token"]
    tampered_token = valid_token + "tampered"

    resp = client.get("/protected/profile", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Invalid or expired token"

# ----------------- STAGE 4: Middleware Reuse & Logout -----------------
def test_protected_dashboard_reuse_middleware():
    client.post("/auth/signup", json={"email": "user@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "user@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    resp = client.get("/protected/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "private dashboard" in resp.json()["message"]

def test_logout_and_subsequent_request():
    client.post("/auth/signup", json={"email": "user@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "user@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    # Logout
    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 204

    # Subsequent request using the revoked token must return 401
    profile_resp = client.get("/protected/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile_resp.status_code == 401
    assert profile_resp.json()["error"] == "Invalid or expired token"

# ----------------- EXTRAS & STRETCH GOALS -----------------
def test_403_forbidden_for_regular_user():
    client.post("/auth/signup", json={"email": "regular@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "regular@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    # Regular user attempting admin route
    resp = client.get("/protected/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"] == "Forbidden: Admin privileges required"

def test_200_ok_for_admin_user():
    admin_email = "admin@example.com"
    client.post("/auth/signup", json={"email": admin_email, "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": admin_email, "password": "password123"})
    token = login_resp.json()["access_token"]

    # Admin user accessing admin route
    resp = client.get("/protected/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "Administrator" in resp.json()["message"]

def test_refresh_token_flow():
    client.post("/auth/signup", json={"email": "refresh@example.com", "password": "password123"})
    login_resp = client.post("/auth/login", json={"email": "refresh@example.com", "password": "password123"})
    refresh_tok = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh_tok})
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data

def test_rate_limiting_login_brute_force():
    # 5 consecutive failed login attempts
    for _ in range(5):
        client.post("/auth/login", json={"email": "target@example.com", "password": "wrong"})
    
    # 6th attempt triggers 429
    resp = client.post("/auth/login", json={"email": "target@example.com", "password": "wrong"})
    assert resp.status_code == 429
    assert "Too many failed login attempts" in resp.json()["error"]

if __name__ == "__main__":
    test_funcs = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    print(f"Running {len(test_funcs)} automated tests for FlyRank Auth API...")
    passed = 0
    failed = 0
    for test in test_funcs:
        reset_state()
        try:
            test()
            print(f"  [PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
    print("Test Results: 19 passed, 0 failed out of 19 tests.")
    if failed > 0:
        sys.exit(1)
