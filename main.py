import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator, root_validator

app = FastAPI(
    title="Task Management API",
    description="A SQLite-backed CRUD API for managing to-do tasks, built with FastAPI, SQLite3, and parameterized SQL queries.",
    version="2.0.0",
    openapi_tags=[
        {"name": "System", "description": "API root discovery and health check endpoints"},
        {"name": "Tasks", "description": "Core CRUD operations and SQL-powered querying for tasks"},
        {"name": "Analytics & Utilities", "description": "Computed metrics and database reset controls"},
    ]
)

DATABASE_FILE = "tasks.db"

def get_db():
    """Establish a connection to the SQLite database with Row mapping enabled."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous = OFF;")
    return conn

def init_db():
    """Create tasks table and indexes if missing, and seed initial tasks inside an atomic transaction."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Schema definition with primary key, typed columns, and audit timestamps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Indexes for fast lookup on filtered and searched columns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);")
        
        # Idempotent seeding: count rows first, insert only if table is empty
        cursor.execute("SELECT COUNT(*) FROM tasks;")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.executemany(
                "INSERT INTO tasks (id, title, done) VALUES (?, ?, ?);",
                [
                    (1, "Buy groceries", 0),
                    (2, "Read FastAPI documentation", 1),
                    (3, "Build CRUD API", 0),
                ]
            )
            conn.commit()

@app.on_event("startup")
def on_startup():
    init_db()

# Auto-initialize database on module load
init_db()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Invalid request body"
    return JSONResponse(status_code=400, content={"error": f"Validation error: {msg}"})

DEFAULT_TASKS = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read FastAPI documentation", "done": True},
    {"id": 3, "title": "Build CRUD API", "done": False},
]

class Task(BaseModel):
    id: int = Field(..., description="Unique integer ID of the task", example=1)
    title: str = Field(..., description="Description or title of the task", example="Buy milk")
    done: bool = Field(..., description="Completion status of the task", example=False)

class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title (required, non-empty)", example="Buy milk")

    @validator("title")
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title is required and cannot be empty")
        return v.strip()

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated task title", example="Buy organic milk")
    done: Optional[bool] = Field(None, description="Updated completion status", example=True)

    @validator("title")
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else v

    @root_validator
    def check_non_empty(cls, values):
        if values.get("title") is None and values.get("done") is None:
            raise ValueError("Empty or invalid body: at least one field ('title' or 'done') must be provided")
        return values

class StatsResponse(BaseModel):
    total: int = Field(..., description="Total number of tasks", example=3)
    done: int = Field(..., description="Number of completed tasks", example=1)
    open: int = Field(..., description="Number of pending/open tasks", example=2)

@app.get(
    "/",
    tags=["System"],
    summary="API Root Information",
    description="Returns API service information, version number, and main endpoint locations."
)
def get_root():
    return {
        "name": "Task API",
        "version": "2.0",
        "endpoints": ["/tasks"]
    }

@app.get(
    "/health",
    tags=["System"],
    summary="Service Health Check",
    description="Returns operational health status of the API server."
)
def health_check():
    return {"status": "ok"}

@app.get(
    "/tasks",
    response_model=List[Task],
    tags=["Tasks"],
    summary="List and Filter Tasks",
    description="Retrieve tasks from SQLite with optional filtering by status (done), substring search (LIKE), sorting, and database limit/offset pagination."
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status (true/false)"),
    search: Optional[str] = Query(None, description="Search case-insensitive substring in task titles using SQL LIKE"),
    sort: Optional[str] = Query(None, description="Sort field ('title' or 'id')"),
    order: Optional[str] = Query("asc", description="Sort order ('asc' or 'desc')"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of items to skip from beginning")
):
    query = "SELECT id, title, done FROM tasks"
    conditions = []
    params = []

    if done is not None:
        conditions.append("done = ?")
        params.append(1 if done else 0)

    if search is not None:
        conditions.append("title LIKE ?")
        params.append(f"%{search.strip()}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Sorting
    sort_col = "title" if sort == "title" else "id"
    sort_dir = "DESC" if order and order.lower() == "desc" else "ASC"
    query += f" ORDER BY {sort_col} {sort_dir}"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)
    elif offset is not None:
        query += " LIMIT -1 OFFSET ?"
        params.append(offset)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]

@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Get Single Task by ID",
    description="Retrieve a single task from SQLite using a parameterized query."
)
def get_task(task_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?;", (task_id,))
        row = cursor.fetchone()
        if not row:
            return JSONResponse(
                status_code=404,
                content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
            )
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

@app.post(
    "/tasks",
    response_model=Task,
    status_code=201,
    tags=["Tasks"],
    summary="Create New Task",
    description="Insert new task into SQLite database with parameterized SQL."
)
def create_task(task_data: TaskCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, done) VALUES (?, 0);",
            (task_data.title,)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?;", (new_id,))
        row = cursor.fetchone()
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Update Existing Task",
    description="Update task title and/or done status in SQLite using parameterized SQL."
)
def update_task(task_id: int, task_data: TaskUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?;", (task_id,))
        current = cursor.fetchone()
        if not current:
            return JSONResponse(
                status_code=404,
                content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
            )
        
        new_title = task_data.title if task_data.title is not None else current["title"]
        new_done = int(task_data.done) if task_data.done is not None else current["done"]
        
        cursor.execute(
            "UPDATE tasks SET title = ?, done = ?, updated_at = datetime('now') WHERE id = ?;",
            (new_title, new_done, task_id)
        )
        conn.commit()
        
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?;", (task_id,))
        updated = cursor.fetchone()
        return {"id": updated["id"], "title": updated["title"], "done": bool(updated["done"])}

@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["Tasks"],
    summary="Delete Task",
    description="Remove a task from SQLite by ID. Returns 204 No Content upon success."
)
def delete_task(task_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = ?;", (task_id,))
        if not cursor.fetchone():
            return JSONResponse(
                status_code=404,
                content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
            )
        cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        conn.commit()
        return Response(status_code=204)

@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Analytics & Utilities"],
    summary="Task Statistics",
    description="Computes aggregate metrics directly in SQLite using SELECT COUNT(*) and WHERE clauses."
)
def get_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks;")
        total_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = 1;")
        done_count = cursor.fetchone()[0]
        open_count = total_count - done_count
        return {"total": total_count, "done": done_count, "open": open_count}

@app.post(
    "/reset",
    tags=["Analytics & Utilities"],
    summary="Reset Seed Tasks",
    description="Atomically resets the SQLite tasks table back to initial 3 seed items."
)
def reset_tasks():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='tasks';")
        cursor.executemany(
            "INSERT INTO tasks (id, title, done) VALUES (?, ?, ?);",
            [
                (1, "Buy groceries", 0),
                (2, "Read FastAPI documentation", 1),
                (3, "Build CRUD API", 0),
            ]
        )
        conn.commit()
        cursor.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
        rows = cursor.fetchall()
        return {
            "message": "Tasks successfully reset to initial seed data",
            "tasks": [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
