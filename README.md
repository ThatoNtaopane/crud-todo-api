# FlyRank Backend Track · Week 2 · Assignment A4: Auth · Login & Protect (Python Lane)

A secure, production-grade RESTful authentication API built with **Python 3.11**, **FastAPI**, **Supabase Auth (GoTrue IdP)**, and **Swagger UI Bearer Authentication**.

---

## 1. What This Is

This project fulfills **Assignment A4 (Auth · Login & Protect)** of the **FlyRank Backend Internship Track**. It transforms an open API into a hardened, identity-aware system. 

Instead of rolling custom password hashing or storing credentials directly, the application delegates user identity management to **Supabase Auth** as a trusted **Identity Provider (IdP)**. The server verifies cryptographically signed **JSON Web Tokens (JWTs)** via reusable dependency guards, enforces strict role-based access control (`401 Unauthorized` vs `403 Forbidden`), and exposes interactive OpenAPI documentation with Swagger Bearer padlocks.

### Core Architectural Concepts
* **The Trust Triangle**: Clear separation of responsibilities between Client, Backend Server, and Supabase IdP.
* **Stateless JWT Verification**: Fast, cryptographically secure validation via `supabase.auth.get_user(token)`.
* **Guard Middleware / Dependency Pattern**: Reusable FastAPI `Depends(get_current_user)` enforcing security before route execution.
* **Granular Status Semantics**: Correct machine-readable HTTP codes (`200`, `201`, `204`, `400`, `401`, `403`, `429`).
* **Interactive OpenAPI / Swagger UI**: Built-in interactive testing with `HTTPBearer` authorization.

---

## 2. Quickstart & Installation

### Prerequisites
* Python 3.10+
* Git
* A free Supabase Project (or use the included mock mode for local testing)

### One Documented Command to Run
```bash
git clone https://github.com/ThatoNtaopane/crud-todo-api.git && cd crud-todo-api && pip install -r requirements.txt && cp .env.example .env && uvicorn main:app --reload --port 8000
```

Once running, the server is available at:
* **API Base URL**: `http://localhost:8000`
* **Interactive Swagger UI**: `http://localhost:8000/docs`
* **OpenAPI Specification**: `http://localhost:8000/openapi.json`
* **Health Check**: `http://localhost:8000/health`

### Environment Configuration (.env)
Create a `.env` file in the project root (copied from `.env.example`):
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
PORT=8000
ADMIN_EMAILS=admin@example.com,thatontaopane@gmail.com
```

> **Crucial Security Rule**: Never commit `.env` to Git. The `.gitignore` file strictly excludes `.env` to prevent accidental credential leakage.

---

## 3. Endpoints Reference Table

| Method | Endpoint | Auth Required | Status Codes | Description | Request Body Example | Response Example |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/` | None | `200` | Root service discovery | None | `{"name": "FlyRank Auth API", "version": "2.0.0"}` |
| **GET** | `/health` | None | `200` | Operational health check | None | `{"status": "ok"}` |
| **POST** | `/auth/signup` | None | `201`, `400` | Register a new user | `{"email": "u@test.com", "password": "pwd"}` | `{"id": "...", "email": "u@test.com"}` |
| **POST** | `/auth/login` | None | `200`, `400`, `401`, `429` | Authenticate & issue JWT | `{"email": "u@test.com", "password": "pwd"}` | `{"access_token": "...", "token_type": "bearer"}` |
| **POST** | `/auth/refresh` | None | `200`, `400`, `401` | Exchange refresh token | `{"refresh_token": "..."}` | `{"access_token": "...", "expires_in": 3600}` |
| **POST** | `/auth/logout` | `Bearer <JWT>` | `204`, `401` | Revoke session / sign out | None | Empty body (`204 No Content`) |
| **GET** | `/public/info` | None | `200` | Public open lobby | None | `{"message": "Welcome stranger! This info is public."}` |
| **GET** | `/protected/profile` | `Bearer <JWT>` | `200`, `401` | Fetch verified user profile | None | `{"id": "...", "email": "...", "created_at": "..."}` |
| **GET** | `/protected/dashboard` | `Bearer <JWT>` | `200`, `401` | Guarded user dashboard | None | `{"message": "Welcome...", "stats": {...}}` |
| **GET** | `/protected/admin` | `Bearer <JWT>` | `200`, `401`, `403` | Admin-only restricted area | None | `{"message": "Welcome Administrator...", ...}` |

---

## 4. Live Verification Outputs (curl -i)

### 4.1. User Registration (POST /auth/signup)
```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```
```http
HTTP/1.1 201 Created
content-type: application/json

{"id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","email":"test@example.com","created_at":"2026-10-12T21:40:00Z","message":"User registered successfully"}
```

### 4.2. User Authentication (POST /auth/login)
```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```
```http
HTTP/1.1 200 OK
content-type: application/json

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpcy1pcy1hLXJlZnJlc2gtdG9rZW4...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {"id":"3fa85f64...","email":"test@example.com"}
}
```

### 4.3. Protected Route with Valid Bearer Token (GET /protected/profile)
```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <PASTE_ACCESS_TOKEN_HERE>"
```
```http
HTTP/1.1 200 OK
content-type: application/json

{"id":"3fa85f64...","email":"test@example.com","created_at":"2026-10-12T21:40:00Z"}
```

### 4.4. Protected Route with Tampered / Invalid Token (401 Unauthorized)
```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer invalid_or_tampered_token_xyz"
```
```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Invalid or expired token"}
```

### 4.5. Missing Token Protection (401 Unauthorized)
```bash
curl -i http://localhost:8000/protected/profile
```
```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Access token required"}
```

### 4.6. Authorization vs Authentication (403 Forbidden Case)
```bash
curl -i http://localhost:8000/protected/admin \
  -H "Authorization: Bearer <REGULAR_USER_TOKEN>"
```
```http
HTTP/1.1 403 Forbidden
content-type: application/json

{"error":"Forbidden: Admin privileges required"}
```

---

## 5. Architectural Deep Dive: Security Engineering Lessons

### 5.1. Authentication (401) vs Authorization (403)
* **401 Unauthorized**: *"Who are you?"* The request failed because authentication credentials were missing, malformed, expired, or invalid. The client must authenticate to proceed.
* **403 Forbidden**: *"I know who you are, and you are not allowed."* The user's identity is verified and legitimate, but their role or permissions do not permit access to this specific resource. Re-authenticating with the same credentials will not change the outcome.

### 5.2. Anatomy of a JSON Web Token (JWT)
A JWT consists of three Base64URL-encoded strings separated by dots (`.`):
1. **Header**: Contains the token type (`JWT`) and signing algorithm (`HS256` or `RS256`).
2. **Payload (Claims)**: Contains statements about the entity (e.g., `sub` (user ID), `email`, `iat`, `exp`).
3. **Signature**: Cryptographic proof generated using the secret key or private key.
> **Iron Rule**: Never store secrets, passwords, or sensitive PII inside a JWT payload. Anyone who intercepts or reads the token can decode the Base64 payload instantly at `jwt.io` without knowing the secret key!

### 5.3. Why Access Tokens are Short-Lived & How Refresh Tokens Work
Access tokens are designed with short lifespans (typically 15 to 60 minutes) to minimize the vulnerability window if a token is intercepted or leaked. Refresh tokens are long-lived, securely stored tokens that allow clients to request a new access token without re-entering credentials.

### 5.4. Stateless JWTs and the "Instant Logout" Dilemma
Because JWT verification is stateless, the server does not check a database table for every request. If a user logs out, their existing JWT remains mathematically valid until its `exp` timestamp passes unless the backend implements an active token revocation list (blacklist) or utilizes Supabase session tracking.

### 5.5. Brute-Force Protection & Rate Limiting
Authentication endpoints (`/auth/login`) are the primary target of automated credential stuffing and brute-force attacks. Rate limiting tracks failed login attempts and returns `429 Too Many Requests` after a threshold (5 failed attempts within 5 minutes), thwarting automated attackers.

---

## 6. Swagger UI & Interactive Documentation

FastAPI automatically provisions interactive Swagger UI at `/docs`. With `HTTPBearer` configured, an **Authorize** button appears with a lock icon. 

![Swagger UI Documentation](docs/swagger-ui.png)

1. Navigate to `http://localhost:8000/docs` in your browser.
2. Click **Authorize** at the top right.
3. Paste your JWT access token from `/auth/login`.
4. Click **Authorize**, then test any locked endpoint (`/protected/profile`, `/protected/dashboard`).


---

## 7. Stage 7: The AI Rematch ("AI vs Me")

In this stage, an AI model was prompted from memory to build the identical secured FastAPI + Supabase API. The generated code was quarantined in `ai-version/` and subjected to peer code review against our Stage 0–6 implementation.

### 7.1. The Memory Prompt
```text
Build a complete, secure REST API using Python and FastAPI that integrates with Supabase Auth as the Identity Provider.
Include POST /auth/signup (201), POST /auth/login (200), POST /auth/logout (204), GET /public/info (200), and GET /protected/profile (200/401).
Validate all input (400), verify Bearer tokens with Supabase get_user, use reusable dependency guards, and configure Swagger UI HTTPBearer padlock.
```

### 7.2. Three Key Code Review Findings

1. **Token Extraction and Malformed Header Handling**:
   * *AI Version*: Used `HTTPBearer()` with default `auto_error=True`. When an `Authorization` header was missing, FastAPI raised its default internal exception returning `{"detail": "Not authenticated"}` rather than our required assignment-specified error `{ "error": "Access token required" }`.
   * *Our Version*: Configured `HTTPBearer(auto_error=False)` with a custom authentication exception handler, properly extracting and sanitizing the Bearer prefix and returning the exact standardized `{ "error": ... }` JSON contract.

2. **Security Flaws & Validation Behavior**:
   * *AI Version*: Relied on Pydantic's default `EmailStr` and field validation, which triggers HTTP `422 Unprocessable Entity` rather than the required HTTP `400 Bad Request`. Furthermore, the AI code blindly trusted network calls without managing connection timeouts or distinguishing between network outages and invalid tokens.
   * *Our Version*: Implemented custom `RequestValidationError` handling to return `400 Bad Request`. Provided safe error isolation so downstream database details or service secrets are never leaked to external clients.

3. **Silent Decisions & Prompt Blindspots**:
   * *What the prompt forgot*: The prompt did not specify the exact format of error JSON responses, how to handle token revocation upon logout, or rate-limiting against credential stuffing.
   * *What the AI silently decided*: The AI silently chose async HTTP calls (`httpx.AsyncClient`) without connection pooling, returned `422` instead of `400`, and treated logout as a no-op returning `None` rather than invalidating the active session.

### 7.3. The Rematch Iteration
We refined our prompt with strict constraints (specifying `400 Bad Request` overrides, `HTTPBearer(auto_error=False)`, `403 Forbidden` admin authorization, and login rate limiting). The regenerated code (`ai-version/main_v2.py`) resolved the validation contract and added role verification.

> **Engineering Takeaway**: *An AI's output is only as good as your technical specification — and you can only effectively judge and audit it because you built the architecture by hand first.*
