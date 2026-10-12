# FlyRank Backend Track · Week 3 · Assignment A2: Connecting Your CRUD to the Database (Python Lane)

A persistent, production-structured RESTful CRUD API that stores tasks in a disk-backed **SQLite** database, built with **Python 3.10+**, **FastAPI**, **SQLite3**, **Pydantic**, and **Swagger UI / OpenAPI 3.0**.

![DB Browser for SQLite](docs/db-browser-tasks.png)

---

## 1. What This Is

This project is the direct sequel to **Assignment A1 (Build your first CRUD API)** for the **FlyRank Backend Internship**. In Assignment 1, the API stored data in an ephemeral in-memory Python list—meaning all state vanished every time the server restarted.

In **Week 3 (Assignment A2)**, we replaced the in-memory storage layer with a persistent, serverless **SQLite** database (`tasks.db`). 

### Core Architectural Principle: Storage as an Implementation Detail
The public API contracts, endpoints, request schemas, validation rules, and response shapes remain **100% identical** to Assignment 1. Clients send the same HTTP requests and receive the same responses. Only the underlying storage engine changed—swapping memory for disk. 

Because the API describes *what* the application does, and the database describes *where* it stores state, our automated test suite passes seamlessly across both implementations. Storage is truly just an implementation detail.

---

## 2. Why SQLite Was Chosen

1. **Zero Configuration & Serverless**: SQLite requires no external daemon, background service, or network socket. The entire engine runs embedded within the Python application process via the standard library (`sqlite3`).
2. **Single-File Portability**: The entire database lives in a single compact file (`tasks.db`) right alongside the code.
3. **Guaranteed Durability & Crash Safety**: SQLite implements full ACID (Atomicity, Consistency, Isolation, Durability) guarantees, writing transactions to disk so data reliably survives process crashes, server restarts, and reboots.
4. **Instant Startup**: There is zero connection handshake latency or network overhead, making it ideal for microservices, embedded applications, and testing environments.

---

## 3. Database Architecture & Location

* **Database File**: `tasks.db` located at the root of the project.
* **Automatic Creation**: The database file, table schema, and indexes are generated automatically on startup (`init_db()`). No manual SQL scripts or database migrations need to be run before launching.
* **Git-Ignored**: `tasks.db` is included in `.gitignore` so that every fresh git clone starts clean and creates its own local instance.
* **Table Schema**:
  ```sql
  CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      done INTEGER NOT NULL DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
  );
  ```
* **Performance Indexes**:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
  CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);
  ```
  *What an index is for:* An index is a dedicated B-tree data structure that allows the database engine to locate matching rows in $O(\log N)$ time instead of scanning every single row in the table ($O(N)$ full table scan).
* **Atomic Seeding Transaction**:
  Seeding the three default tasks is wrapped in an atomic database transaction (`conn.commit()`) preceded by `SELECT COUNT(*) FROM tasks;`.
  *Why transactions matter:* Wrapping multi-step writes in a transaction ensures all-or-nothing atomicity; if any single insertion fails, the entire batch rolls back, preventing corrupt, half-seeded states.

---

## 4. How to Install and Run

### Prerequisites
- Python 3.10+
- Git

### One Documented Command to Run
Clone the repository and launch the server in a single command:

```bash
git clone https://github.com/ThatoNtaopane/crud-todo-api.git && cd crud-todo-api && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
```

On first launch, `tasks.db` is created automatically, and `GET /tasks` will return the 3 seeded tasks immediately.

### Key Service URLs
- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON Specification**: `http://localhost:8000/openapi.json`
- **Health Check**: `http://localhost:8000/health`

### Automated Test Suite Execution
Run the full 24-case automated test suite (validating all endpoints, status codes, restart persistence, and SQL injection safety):

```bash
python3 test_api.py
```

---

## 5. Endpoints Reference Table

| Method | Endpoint | Status Codes | Description | Request Body Example | Response Body Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/` | `200` | API service discovery & root metadata | *None* | `{"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}` |
| **GET** | `/health` | `200` | Health check endpoint | *None* | `{"status": "ok"}` |
| **GET** | `/tasks` | `200` | List & filter tasks (SQL `LIKE`, `done`, `sort`, `limit`, `offset`) | *None* | `[{"id": 1, "title": "Buy groceries", "done": false}, ...]` |
| **GET** | `/tasks/{id}` | `200`, `404` | Parameterized single-task fetch by ID | *None* | `{"id": 1, "title": "Buy groceries", "done": false}` |
| **POST** | `/tasks` | `201`, `400` | Create new task (SQL `INSERT`, auto ID, `done=0`) | `{"title": "Buy milk"}` | `{"id": 4, "title": "Buy milk", "done": false}` |
| **PUT** | `/tasks/{id}` | `200`, `400`, `404` | Parameterized `UPDATE` for title and/or done | `{"title": "Updated", "done": true}` | `{"id": 1, "title": "Updated", "done": true}` |
| **DELETE** | `/tasks/{id}` | `204`, `404` | Parameterized `DELETE` from SQLite | *None* | *Empty body* |
| **GET** | `/stats` | `200` | Real metrics computed with SQL `SELECT COUNT(*)` | *None* | `{"total": 3, "done": 1, "open": 2}` |
| **POST** | `/reset` | `200` | Atomically reset SQLite table to initial 3 seed items | *None* | `{"message": "Tasks successfully reset...", "tasks": [...]}` |

---

## 6. Stage 4: Manual SQL Exploration

During Stage 4, `tasks.db` was inspected directly using DB Browser for SQLite and raw SQL queries:

```sql
-- 1. List every task
SELECT * FROM tasks;

-- 2. Filter for only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- 3. Count total tasks
SELECT COUNT(*) FROM tasks;

-- 4. Mark every task as completed
UPDATE tasks SET done = 1;

-- 5. Delete all completed tasks
DELETE FROM tasks WHERE done = 1;
```

### Stage 4 Checkpoint Results: Direct Database Manipulation & Instant Sync
* **Example Query**:
  ```sql
  SELECT id, title, done FROM tasks WHERE done = 1;
  ```
* **Execution Output**:
  ```text
  (2, 'Read FastAPI documentation', 1)
  ```
* **Synchronization Observation**:
  After running `UPDATE tasks SET done = 1;` directly in the database, querying `GET /tasks` from the API immediately returned all tasks with `done: true` without restarting the server. Because the API process and DB Browser read the exact same underlying file (`tasks.db`), there is zero caching delay—the SQLite file is the single, instantaneous source of truth.

---

## 7. Reflection: Schema Evolution & Why Migrations Exist

Adding `created_at` and `updated_at` columns to the `tasks` table highlighted the tension between application evolution and live data. In development, modifying table shape often tempts developers to delete the database and restart fresh. In production, however, live customer data cannot be wiped. 

That visceral friction—needing to alter a table's structure while preserving existing records—is why database migrations exist. Migrations provide version-controlled, incremental, and reversible scripts (such as Alembic or Flyway) that transition database schemas safely across environments.

---

## 8. Bonus Stage: AI vs Me (Code Review & AI Rematch)

In Stage 6, we prompted an AI assistant to migrate the original in-memory API to SQLite and quarantined its code in `ai-version/`.

### 8.1. The AI Prompt
```text
Migrate our existing FastAPI task CRUD API from using an in-memory Python list to a persistent SQLite database using Python's built-in sqlite3 standard library.

Requirements:
1. Database file: Name it tasks.db in the root project folder. It must be created automatically if missing.
2. Schema: A single table named 'tasks' with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), title (TEXT NOT NULL), and done (INTEGER DEFAULT 0).
3. Initial Data: Seed three default tasks ("Buy groceries", "Read FastAPI documentation", "Build CRUD API") only when the database is completely empty. Do not duplicate them on server restarts.
4. Endpoints: Keep the five CRUD endpoints intact with identical paths and request/response contracts:
   - GET /tasks (list all tasks)
   - GET /tasks/{task_id} (fetch one task by ID)
   - POST /tasks (create new task, return 201)
   - PUT /tasks/{task_id} (update title and/or done status, return 200)
   - DELETE /tasks/{task_id} (delete task, return 204 No Content)
5. Safety: All SQL queries MUST use parameterized queries (?) to prevent SQL injection vulnerabilities. Never interpolate user input into SQL strings.
6. Validation & Error Handling: Maintain 400 Bad Request for invalid/empty request bodies, and 404 Not Found for non-existent IDs. Error responses must include JSON error messages.
```

### 8.2. AI Code Review: Three Concrete Differences

1. **What Did the AI Do Better — And Can You Explain It?**
   * *Lean, Direct Return*: In `POST /tasks`, the AI generated the return dictionary directly (`{"id": new_id, "title": payload.title, "done": False}`) without executing a follow-up `SELECT` query. While our production code issued a second `SELECT` to guarantee database-generated timestamps were retrieved, the AI's approach eliminated an extra round-trip query.
2. **What Did the AI Get Wrong or Quietly Ignore?**
   * *Connection Leaking & No Context Managers*: The AI called `sqlite3.connect()` manually inside every function and called `conn.close()` at the end, but did not use Python context managers (`with conn:`). Any exception raised during query execution leaked open connections and file handles.
   * *Tuple Index Slicing vs. Row Mapping*: The AI omitted `conn.row_factory = sqlite3.Row` and instead manually indexed tuples (`r[0]`, `r[1]`, `r[2]`). Any future column addition breaks the entire API.
   * *Error Contract Drift*: The AI defaulted to `raise HTTPException(status_code=404, detail="Task not found")`, producing `{"detail": ...}` instead of the required `{"error": ...}` JSON format from Assignment 1.
3. **What Did the Prompt Forget to Specify — And What Did the AI Silently Decide?**
   * The prompt forgot to specify the exact JSON key for error envelopes (`"error"` vs `"detail"`), connection lifecycle patterns, and query performance indexes. The AI silently chose default FastAPI error formats, unindexed tables, and ad-hoc connection instances.

### 8.3. The Rematch
We hardened the specification in `ai-version/rematch_prompt.txt` to enforce `get_db()` context managers with `row_factory`, explicit `{"error": ...}` exception handlers, and performance indexes. The resulting `ai-version/main_v2.py` achieved full architectural parity.

---

## 9. Git Commit Progression

This repository contains clean, stage-by-stage commits demonstrating the complete migration:
* `Stage 0: create SQLite database`
* `Stage 1: database read endpoints`
* `Stage 2: insert into database`
* `Stage 3: update and delete with SQL`
* `Stage 4: explored SQLite`
* `Extras: search, filters, stats, timestamps, and indexes`
* `Stage 5: database documentation`
* `Stage 6: AI vs me`
