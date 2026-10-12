import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator, root_validator

app = FastAPI(
    title="Task Management API",
    description="A SQLite-backed CRUD API for managing to-do tasks, built with FastAPI and SQLite3.",
    version="2.0.0",
    openapi_tags=[
        {"name": "System", "description": "API root discovery and health check endpoints"},
        {"name": "Tasks", "description": "Core CRUD operations and querying for tasks"},
        {"name": "Analytics & Utilities", "description": "Computed metrics and demo seed controls"},
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
    """Create tasks table if missing and seed initial tasks inside an atomic transaction."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
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

# In-memory tasks variable maintained during transition
tasks = [dict(t) for t in DEFAULT_TASKS]

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
    summary="API Root Information"
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
    summary="Service Health Check"
)
def health_check():
    return {"status": "ok"}

@app.get(
    "/tasks",
    response_model=List[Task],
    tags=["Tasks"],
    summary="List Tasks",
    description="Retrieve tasks from SQLite database."
)
def list_tasks():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
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
    summary="Create New Task"
)
def create_task(task_data: TaskCreate):
    next_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {
        "id": next_id,
        "title": task_data.title,
        "done": False
    }
    tasks.append(new_task)
    return new_task

@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Update Existing Task"
)
def update_task(task_id: int, task_data: TaskUpdate):
    for task in tasks:
        if task["id"] == task_id:
            if task_data.title is not None:
                task["title"] = task_data.title
            if task_data.done is not None:
                task["done"] = task_data.done
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["Tasks"],
    summary="Delete Task"
)
def delete_task(task_id: int):
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(index)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Analytics & Utilities"],
    summary="Task Statistics"
)
def get_stats():
    total_count = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    open_count = total_count - done_count
    return {"total": total_count, "done": done_count, "open": open_count}

@app.post(
    "/reset",
    tags=["Analytics & Utilities"],
    summary="Reset Seed Tasks"
)
def reset_tasks():
    global tasks
    tasks = [dict(t) for t in DEFAULT_TASKS]
    return {
        "message": "Tasks successfully reset to initial seed data",
        "tasks": tasks
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
