# Step-by-Step Instructions: Publishing Week 4 (Assignment A3) to GitHub

Your repository has been completely updated and verified for **FlyRank Internship · Backend Track · Week 1 · Assignment A3: Containerize your stack**.

This complete update includes:
- **PostgreSQL in Docker**: Fully containerized Postgres 15 database service with named volume persistence (`taskdata`).
- **One-Command Orchestration**: Production `compose.yaml` and `Dockerfile` starting the entire stack with `docker compose up --build`.
- **Environment Secrets Management**: Strict `.env` workflow (`.env.example` committed, `.env` git-ignored).
- **Safe Parameterized CRUD**: All 5 CRUD endpoints implemented in `repository.py` using `%s` placeholders and `psycopg` (v3).
- **Automated Health Probes**: Real `/health` check executing `SELECT 1` against PostgreSQL.
- **Stretch Goals & Extras**: Multi-stage Dockerfile optimization (`Dockerfile.multistage`), indexing benchmark with `EXPLAIN ANALYZE`, and the mortality experiment demonstration.
- **Stage 6 AI Rematch**: Complete quarantined `ai-version/` directory with prompt, code, diff patch, and rematch analysis.
- **Verified Commit Progression**: 8 sequential, honest stage commits (`Stage 0` through `Stage 6` + `Extras`).

---

## Method 1: Using the Pre-Packaged Archive from Google Drive (Recommended)

The entire repository with its full Git history has been archived into `crud-todo-api-docker-postgres.zip` and uploaded to your Google Drive folder:
**`Flyrank AI / FlyRank - Week 4 - Containerize your stack`**

### Step 1: Download and Extract
1. Open Google Drive and navigate to `FlyRank - Week 4 - Containerize your stack`.
2. Download `crud-todo-api-docker-postgres.zip`.
3. Unzip the archive into your local development workspace:
   ```bash
   unzip crud-todo-api-docker-postgres.zip -d crud-todo-api-a3
   cd crud-todo-api-a3
   ```

### Step 2: Verify Git History
Verify that all stage commits are present:
```bash
git log --oneline -n 15
```
You will see the complete commit chain from Assignment A1, Assignment A2, and Assignment A3:
- `Stage 6: AI vs me`
- `Extras: database health check, indexes, and multi-stage Dockerfile`
- `Stage 5: one-command stack + docs`
- `Stage 4: docker-compose the whole stack`
- `Stage 3: full CRUD on Postgres`
- `Stage 2: read from Postgres`
- `Stage 1: connect via .env and create table`
- `Stage 0: Postgres in Docker + gitignore`

### Step 3: Push to Your Public GitHub Repository
Link your remote repository and push:
```bash
# Verify or update your remote URL
git remote set-url origin https://github.com/ThatoNtaopane/crud-todo-api.git

# Push the updated main branch to GitHub
git push origin main
```
*(If prompted or if GitHub has remote commits, run `git pull --rebase origin main` before pushing).*

---

## Method 2: Testing and Running Locally with One Command

### 1. Start the Complete Stack
From the project root:
```bash
cp .env.example .env
docker compose up --build
```
Docker Compose will:
1. Build the lightweight Python 3.11 FastAPI image.
2. Pull and start `postgres:15-alpine`.
3. Run the health check (`pg_isready -U postgres -d tasks`).
4. Launch the API once the database is healthy.
5. Auto-create the `tasks` table and seed the initial 3 tasks.

### 2. Verify Endpoints via curl
In a new terminal window:
```bash
# Check service and database health
curl -i http://localhost:3000/health

# List tasks (returns 3 seeded tasks)
curl -i http://localhost:3000/tasks

# Create a new task
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Verify containerized stack"}'
```

### 3. Verify Persistence Across Teardown
```bash
# Tear down containers and network
docker compose down

# Start up again
docker compose up -d

# Verify previously created task is still there!
curl -i http://localhost:3000/tasks
```

### 4. Run the Automated Test Suite
```bash
python3 test_api.py
```
Expected output:
```text
Running automated test suite for Containerized PostgreSQL CRUD API...
All 24 test cases passed successfully!
```

---

## Submission Checklist

- [x] PostgreSQL runs in an isolated container; whole stack starts with `docker compose up`.
- [x] Application connects using `DATABASE_URL` from `.env` (`.env` git-ignored, `.env.example` committed).
- [x] `tasks` table created automatically with SERIAL primary key and audit timestamps.
- [x] 3 example tasks seeded only on first run (seed-once rule verified).
- [x] All 5 CRUD endpoints working against Postgres using parameterized queries (`%s`).
- [x] Proper HTTP status codes: `200`, `201`, `204`, `400` (invalid body), `404` (unknown ID) with JSON error messages.
- [x] Data persistence proven across full `docker compose down` and `docker compose up` via named volume `taskdata`.
- [x] `README.md` updated with one-command run, `.env.example`, endpoint table, `curl -i` logs, and database screenshot (`docs/postgres-tasks-psql.png`).
- [x] Automated test suite with 24 passing test cases.
- [x] Clean Git commit history with >= 6 honest stage commits.
- [x] Bonus Stage 6 completed with AI quarantine directory (`ai-version/`) and README diff review.
