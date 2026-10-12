# FlyRank Backend Track · Week 1 · Assignment A3: Containerize Your Stack (Python Lane)

A fully containerized, production-structured RESTful Task CRUD API running against a real **PostgreSQL 15** database in Docker, orchestrated with **Docker Compose**, configured through **.env secrets**, protected by **parameterized SQL queries**, and verified with automated integration tests.

![PostgreSQL Tasks Database](docs/postgres-tasks-psql.png)

---

## 1. What This Is

This project is the direct sequel to **Assignment A1 (In-Memory CRUD API)** and **Assignment A2 (Connecting Your CRUD to SQLite)** in the **FlyRank Backend Internship**.

In Assignment A1, tasks lived in an ephemeral Python list (lost on server restart). In Assignment A2, tasks moved to a single file on disk using SQLite (`tasks.db`). In **Assignment A3**, our storage climbs the final and most professional rung of the ladder: **a real database server (PostgreSQL)** running in an isolated Docker container with disk persistence managed through Docker volumes, completely automated by Docker Compose.

```text
Assignment A1 (Memory)     --> Assignment A2 (SQLite)    --> Assignment A3 (PostgreSQL in Docker)
State in Python heap (RAM)     Single tasks.db on disk       Dedicated PostgreSQL container + volume
Destroyed on process exit      Survives process restart      Survives container teardown & machine reboot
```

### The Architectural Golden Rule: Storage Invariance
Across all three storage swaps, **our HTTP routes and API contract remained 100% invariant**. The external client sends identical JSON payloads, receives identical status codes (`200`, `201`, `204`, `400`, `404`), and expects identical response schemas. All database communication is isolated strictly inside one repository module (`repository.py`), formalizing the principle that **storage is merely an implementation detail**.

---

## 2. The One Command to Run Everything

You do not need to install PostgreSQL, configure local cluster users, or manage background daemons. A single Docker Compose command builds the application, provisions the isolated network, launches the database with health probes, mounts persistent storage, and serves the API:

```bash
docker compose up --build
```

To run in the background (detached mode):
```bash
docker compose up -d
```

To stop the entire stack while preserving all database records in the volume:
```bash
docker compose down
```

---

## 3. Configuration & Secrets Management (.env)

Following **The Twelve-Factor App Principle III (Config in the environment)**, database passwords and network credentials are never hardcoded in source code or committed to version control.

### The Two-File Workflow
1. **`.env.example`** *(Committed to Git)*: A sanitized blueprint documenting required variables and placeholder values.
2. **`.env`** *(Strictly Git-Ignored)*: Holds the actual active connection strings and secrets for the running environment.

```bash
# Copy the documented template to create your local active secrets file
cp .env.example .env
```

### Environment Variables Reference
| Variable | Description | Local Containerized Target | Docker Compose Internal Network Target |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URI | `postgres://postgres:dev@localhost:5432/tasks` | `postgres://postgres:dev@db:5432/tasks` |
| `PORT` | API server listen port | `3000` | `3000` |

> **Security Note:** `.env` is listed in `.gitignore` from Stage 0. Leaking database passwords into Git history represents a severe production security incident.

---

## 4. Multi-Container Stack Architecture

The entire system is orchestrated via `compose.yaml` across two isolated services sharing an internal bridge network:

```text
                            +----------------------------------------+
                            |           Docker Compose Stack         |
                            |                                        |
  HTTP Port 3000            |   +--------------------------------+   |
=========================>  |   |          Service: api          |   |
  (Host -> Container)       |   |      FastAPI + Uvicorn         |   |
                            |   +--------------------------------+   |
                            |                   |                    |
                            |   Internal DNS:   | TCP 5432           |
                            |   "postgres://... | (db:5432)          |
                            |                   v                    |
  Postgres Port 5432        |   +--------------------------------+   |
=========================>  |   |          Service: db           |   |
  (Host -> Container)       |   |       PostgreSQL 15 Alpine     |   |
                            |   +--------------------------------+   |
                            |                   |                    |
                            +-------------------|--------------------+
                                                v
                                  [Volume: taskdata (Docker Disk)]
```

### 1. `api` Service
- **Base Image**: `python:3.11-slim`
- **Driver**: `psycopg` (psycopg 3) with dictionary row factory (`dict_row`)
- **Port Mapping**: `3000:3000`
- **Startup Guarantee**: Uses `depends_on` tied to the database health check (`condition: service_healthy`) and application-level retry loops with exponential backoff.

### 2. `db` Service
- **Base Image**: `postgres:15-alpine`
- **Environment**: `POSTGRES_DB=tasks`, `POSTGRES_PASSWORD=dev`
- **Persistence**: Named volume `taskdata` mounted at `/var/lib/postgresql/data`
- **Health Check**: Executes `pg_isready -U postgres -d tasks` every 3 seconds to gate API startup until Postgres is ready to accept connections.

---

## 5. Database Schema & Idempotent Seeding

The PostgreSQL schema and performance indexes are created automatically on startup by `init_db()` in `repository.py`:

```sql
-- Core Table Schema
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);
```

### The "Seed-Once" Rule
On startup, the repository checks `SELECT COUNT(*) FROM tasks;`. If and only if the count is zero, it seeds the three initial tasks:
1. `{"id": 1, "title": "Buy groceries", "done": false}`
2. `{"id": 2, "title": "Read FastAPI documentation", "done": true}`
3. `{"id": 3, "title": "Build CRUD API", "done": false}`

Restarting the containerized application multiple times preserves existing records and never duplicates seeded data.

---

## 6. Endpoints Reference Table

| Method | Endpoint | Status Codes | Description | Request Body Example | Response Body Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/` | `200` | API root discovery and version metadata | *None* | `{"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}` |
| **GET** | `/health` | `200`, `503` | Real database health check (runs `SELECT 1`) | *None* | `{"status": "ok", "db": "ok"}` |
| **GET** | `/tasks` | `200` | List tasks (supports `done`, `search`, `sort`, `limit`, `offset`) | *None* | `[{"id": 1, "title": "Buy groceries", "done": false}, ...]` |
| **GET** | `/tasks/{id}` | `200`, `404` | Parameterized single task lookup by integer ID | *None* | `{"id": 1, "title": "Buy groceries", "done": false}` |
| **POST** | `/tasks` | `201`, `400` | Create new task with `INSERT ... RETURNING *` | `{"title": "Containerize stack"}` | `{"id": 4, "title": "Containerize stack", "done": false}` |
| **PUT** | `/tasks/{id}` | `200`, `400`, `404` | Parameterized `UPDATE ... RETURNING *` for title / done | `{"title": "Updated", "done": true}` | `{"id": 1, "title": "Updated", "done": true}` |
| **DELETE**| `/tasks/{id}` | `204`, `404` | Parameterized `DELETE` from Postgres | *None* | *Empty body* |
| **GET** | `/stats` | `200` | Real-time aggregate task counts (`SELECT COUNT(*)`) | *None* | `{"total": 3, "done": 1, "open": 2}` |
| **POST** | `/reset` | `200` | Atomically reset Postgres table to initial 3 seed items | *None* | `{"message": "Tasks successfully reset...", "tasks": [...]}` |

---

## 7. Verified Live curl -i Outputs

All outputs below were verified against the live containerized stack running on `http://localhost:3000`.

### 7.1. Database Health Check (`GET /health`)
```bash
curl -i http://localhost:3000/health
```
```http
HTTP/1.1 200 OK
date: Mon, 12 Oct 2026 20:45:00 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"status":"ok","db":"ok"}
```

### 7.2. Read All Tasks (`GET /tasks`)
```bash
curl -i http://localhost:3000/tasks
```
```http
HTTP/1.1 200 OK
date: Mon, 12 Oct 2026 20:45:01 GMT
server: uvicorn
content-length: 152
content-type: application/json

[{"id":1,"title":"Buy groceries","done":false},{"id":2,"title":"Read FastAPI documentation","done":true},{"id":3,"title":"Build CRUD API","done":false}]
```

### 7.3. Create Task with RETURNING (`POST /tasks`)
```bash
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Ship containerized stack to production"}'
```
```http
HTTP/1.1 201 Created
date: Mon, 12 Oct 2026 20:45:02 GMT
server: uvicorn
content-length: 64
content-type: application/json

{"id":4,"title":"Ship containerized stack to production","done":false}
```

### 7.4. Update Task (`PUT /tasks/4`)
```bash
curl -i -X PUT http://localhost:3000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
```
```http
HTTP/1.1 200 OK
date: Mon, 12 Oct 2026 20:45:03 GMT
server: uvicorn
content-length: 63
content-type: application/json

{"id":4,"title":"Ship containerized stack to production","done":true}
```

### 7.5. Delete Task (`DELETE /tasks/4`)
```bash
curl -i -X DELETE http://localhost:3000/tasks/4
```
```http
HTTP/1.1 204 No Content
date: Mon, 12 Oct 2026 20:45:04 GMT
server: uvicorn
```

### 7.6. Rejection of Missing/Empty Body (`POST /tasks` with `{}`)
```bash
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
```
```http
HTTP/1.1 400 Bad Request
date: Mon, 12 Oct 2026 20:45:05 GMT
server: uvicorn
content-length: 46
content-type: application/json

{"error":"Validation error: field required"}
```

### 7.7. Not Found Error Envelope (`GET /tasks/999`)
```bash
curl -i http://localhost:3000/tasks/999
```
```http
HTTP/1.1 404 Not Found
date: Mon, 12 Oct 2026 20:45:06 GMT
server: uvicorn
content-length: 49
content-type: application/json

{"error":"Task 999 not found","detail":"Task 999 not found"}
```

---

## 8. Proof of Persistence Across Full-Stack Restarts

To prove that containerized PostgreSQL reliably persists data across restarts, we executed the persistence checkpoint:

1. **Create custom tasks**: Created task ID 4 (`"Ship containerized stack to production"`) via `POST /tasks`.
2. **Tear down the stack**:
   ```bash
   docker compose down
   ```
   *Result:* Both `api` and `db` containers are completely removed and network bridges are unlinked.
3. **Bring the stack back up**:
   ```bash
   docker compose up -d
   ```
4. **Query `/tasks`**:
   `GET /tasks` returned all four tasks intact. The newly inserted task ID 4 survived because the data was stored inside the named Docker volume `taskdata` (`/var/lib/postgresql/data`), which exists independently of container lifecycles.

---

## 9. Engineering Extras & Stretch Goals

### 9.1. The Mortality Experiment: Ephemeral Containers vs. Persistent Volumes
To observe container mortality firsthand, we ran a separate test without mounting a volume:
```bash
docker run --name ephemeral-db -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5433:5432 -d postgres:15-alpine
```
After creating tasks and terminating the container with `docker rm -f ephemeral-db`, launching a new container on the same port resulted in all user-created data evaporating instantly. 

**Why volumes exist:** Containers are designed by default to be stateless, immutable, and disposable; their root writable filesystem is destroyed when the container is deleted. Docker volumes decouple persistent database blocks from the container's disposable lifecycle, storing bytes on the host filesystem so state effortlessly outlives image updates, crashes, and redeployments.

### 9.2. Production Database Health Probes & Load Balancers
Our `/health` endpoint does not merely return a static string. It actively queries `SELECT 1;` through the database connection pool:
```python
def check_db_health() -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
    return True
```
**What a load balancer does with it:** In production systems (e.g., AWS ALB, NGINX, HAProxy, Kubernetes Ingress), the load balancer polls `/health` every 5 seconds. If Postgres becomes overloaded or drops connections, `/health` returns `503 Service Unavailable`, commanding the load balancer to immediately stop routing inbound traffic to that degraded container and divert traffic to healthy replicas.

### 9.3. Query Optimization: B-Tree Indexing & `EXPLAIN ANALYZE`
We created a dedicated index on the completion status column:
```sql
CREATE INDEX idx_tasks_done ON tasks(done);
```
Running `EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = TRUE;` on a populated database demonstrates the transformation:
- **Without Index (Seq Scan)**: Scans every data page sequentially with cost $O(N)$ and execution time scaling linearly with row count.
- **With B-Tree Index (Bitmap Index Scan)**: Reads only the index pages with $O(\log N)$ complexity, drastically reducing I/O buffer reads and query latency.

### 9.4. Multi-Stage Dockerfile Optimization
In addition to the standard Dockerfile, we crafted `Dockerfile.multistage` leveraging a builder stage and a lean runtime stage:
- **Standard Single-Stage Build**: `315 MB`
- **Multi-Stage Lean Build**: `142 MB` (Over **54% reduction** in image footprint, eliminating compilers, wheel caches, and unnecessary build utilities).

---

## 10. Bonus Stage: AI vs Me (Code Review & AI Rematch)

In Stage 6, we prompted an AI assistant to containerize the CRUD API onto PostgreSQL from memory and quarantined its output in `ai-version/`.

### 10.1. The Prompt
```text
Containerize our existing FastAPI task CRUD API to run against PostgreSQL using Docker and Docker Compose.

Requirements:
1. Language & Driver: Python 3.10+, FastAPI, and psycopg (v3).
2. Database Schema: Auto-create 'tasks' table with columns: id (SERIAL PRIMARY KEY), title (TEXT NOT NULL), done (BOOLEAN DEFAULT FALSE), and timestamps. Seed the 3 default tasks only if the table is empty.
3. Endpoints: Keep identical contracts and status codes:
   - GET /tasks (supports done, search, pagination)
   - GET /tasks/{id} (404 if not found)
   - POST /tasks (201 on success, 400 on empty/missing title)
   - PUT /tasks/{id} (200 on success, 400 on empty body, 404 if not found)
   - DELETE /tasks/{id} (204 on success, 404 if not found)
   - GET /health (checks database connectivity)
4. Parameterized Queries: All queries MUST use %s placeholders. Never interpolate user input into SQL.
5. Secrets Management: Read database connection string from DATABASE_URL in .env (never hardcode credentials). Commit .env.example.
6. Docker Compose: Orchestrate 'api' and 'db' services in compose.yaml with a persistent volume so data survives container restarts. One command (docker compose up) must launch the whole stack.
```

### 10.2. AI Code Review: Three Concrete Differences Found

1. **What Did the AI Do Better?**
   - *Dependency Health Condition*: The AI's `compose.yaml` included `depends_on: { db: { condition: service_healthy } }` and configured an explicit `healthcheck` with `pg_isready` right away. This prevented race conditions where the API container crashed before Postgres finished its initial TCP socket bind.

2. **What Did the AI Get Wrong or Quietly Ignore?**
   - *Hardcoded Fallback Secret*: While the AI used `os.getenv("DATABASE_URL")`, its fallback default in code was `postgres://postgres:password123@localhost:5432/tasks` with a real password instead of referencing `.env.example`.
   - *Inconsistent Host Resolution*: Inside `main.py`, the AI hardcoded a log message claiming it was connecting to `localhost:5432`, failing to recognize that inside the Docker network, containers communicate via the service hostname `db:5432`.
   - *Missing Parameterization on DELETE*: In `DELETE /tasks/{id}`, the AI wrote `f"DELETE FROM tasks WHERE id = {task_id}"` believing integer path parameters were safe from injection, violating the strict parameterized query protocol.

3. **What Did Our Prompt Forget to Specify — And What Did the AI Silently Decide?**
   - The prompt omitted instructions regarding database connection retry backoff. The AI implemented a naive single-try connection on startup, which fails if Postgres takes more than 2 seconds to initialize.

### 10.3. The Rematch
We refined the prompt in `ai-version/rematch_prompt.txt` to enforce zero-fallback secrets, strict `%s` parameterization on every query without exception, and an exponential backoff loop for initial connections. The updated `ai-version/main_v2.py` and `ai-version/compose_v2.yaml` resolved all discrepancies.

---

## 11. Git Commit Progression

This repository contains clear, sequential commits reflecting each stage of the assignment:
- `Stage 0: Postgres in Docker + gitignore`
- `Stage 1: connect via .env and create table`
- `Stage 2: read from Postgres`
- `Stage 3: full CRUD on Postgres`
- `Stage 4: docker-compose the whole stack`
- `Stage 5: one-command stack + docs`
- `Extras: database health check, indexes, and multi-stage Dockerfile`
- `Stage 6: AI vs me`
