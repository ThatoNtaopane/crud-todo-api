# Step-by-Step Instructions: Publishing Week 3 Assignment A2 to GitHub

Your repository has been updated with all Week 3 Assignment A2 stages, including:
- **SQLite Database Architecture**: Automated `tasks.db` creation, schema, and idempotent seeding.
- **Full CRUD Endpoints**: Parameterized queries preventing SQL injection across all routes.
- **Advanced Features & Extras**: Search (`LIKE`), status filters (`done`), sorting, database limit/offset pagination, timestamps, and indexes.
- **Stage 4 SQL Exploration**: Manual queries and direct database sync verification.
- **Stage 6 AI Rematch**: Quarantine directory (`ai-version/`), prompts, v1 and v2 implementations, and diff patch.
- **Complete Git History**: All required sequential stage commits (`Stage 0` through `Stage 6`).

---

## Method 1: Using the Pre-Packaged Repository Archive (Fastest & Easiest)

The complete updated repository has been packaged into `crud-todo-api-sqlite.zip` and uploaded to your Google Drive folder (`FlyRank AI / FlyRank - Week 3 - Connecting your CRUD to the database`).

### Step 1: Download and Extract
1. Open Google Drive and download `crud-todo-api-sqlite.zip`.
2. Extract the archive on your local computer:
   ```bash
   unzip crud-todo-api-sqlite.zip -d crud-todo-api-w3
   cd crud-todo-api-w3
   ```

### Step 2: Push the Updated Commits to GitHub
The repository is already configured with your Git branch (`main`) and commits. To push directly to your existing GitHub repository:

```bash
# Verify commit history
git log --oneline -n 10

# Set or verify remote URL
git remote set-url origin https://github.com/ThatoNtaopane/crud-todo-api.git

# Push the commits to your GitHub repo
git push origin main
```

*(Note: If you have made commits on GitHub in the meantime, run `git pull --rebase origin main` before pushing).*

---

## Method 2: Applying the Updates to Your Existing Local Clone

If you already have your `crud-todo-api` repository cloned locally:

1. Open your terminal in your existing repository:
   ```bash
   cd path/to/crud-todo-api
   ```
2. Copy the updated project files from the downloaded bundle:
   - `main.py`
   - `test_api.py`
   - `README.md`
   - `.gitignore`
   - `docs/db-browser-tasks.png`
   - `scripts/manual_queries.sql`
   - `ai-version/` (entire folder)
3. Review status and commit or push:
   ```bash
   git status
   git push origin main
   ```

---

## Method 3: Verifying Everything Locally

Before submitting to FlyRank, you can verify that the application runs with a single command and passes all automated tests:

### 1. Run the Application
```bash
# Clean start (tasks.db will be created automatically)
uvicorn main:app --reload --port 8000
```

### 2. Verify Endpoints
Open your browser or terminal:
- **Interactive Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs)
- **Get Tasks**:
  ```bash
  curl -i http://localhost:8000/tasks
  ```
  Returns `200 OK` with the 3 seeded tasks from `tasks.db`.

### 3. Run the Automated Test Suite
```bash
python3 test_api.py
```
Expected output:
```text
Running automated test suite for SQLite CRUD API...
All 24 test cases passed successfully!
```

---

## Submission Checklist
- [x] All 5 core CRUD endpoints working against SQLite (`tasks.db`)
- [x] Data persistence verified across server restarts
- [x] Idempotent seed runs once on first startup
- [x] Parameterized SQL placeholders (`?`) used throughout
- [x] Status codes: `200`, `201`, `204`, `400`, `404` with structured JSON error messages
- [x] DB Browser screenshot in `docs/db-browser-tasks.png`
- [x] "AI vs me" section and `ai-version/` directory with diff analysis
- [x] Clean Git commit history with ≥6 stage commits
