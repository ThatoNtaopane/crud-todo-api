"""Task Management CRUD API - Containerized Stack Edition (FastAPI + PostgreSQL)

FlyRank Internship · Backend Track · Week 1 · Assignment A3: Containerize your stack.
All database operations are delegated to repository.py using parameterized PostgreSQL queries.
"""

import os
from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator, root_validator
from dotenv import load_dotenv

import repository

load_dotenv()

app = FastAPI(
    title="Task Management API",
    description="A containerized CRUD API for managing to-do tasks, backed by PostgreSQL in Docker, FastAPI, and parameterized queries.",
    version="3.0.0",
    openapi_tags=[
        {"name": "System", "description": "API root discovery and health check endpoints"},
        {"name": "Tasks", "description": "Core CRUD operations and SQL-powered querying for tasks"},
        {"name": "Analytics & Utilities", "description": "Computed metrics and database reset controls"},
    ]
)


@app.on_event("startup")
def on_startup():
    """Initialize PostgreSQL table schema and seed data on startup."""
    repository.init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic validation errors into standard 400 Bad Request JSON responses."""
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Invalid request body"
    return JSONResponse(status_code=400, content={"error": f"Validation error: {msg}"})


DEFAULT_TASKS = repository.DEFAULT_TASKS


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
    description="Returns operational health status of the API and verifies PostgreSQL database connection."
)
def health_check():
    db_ok = repository.check_db_health()
    if db_ok:
        return {"status": "ok", "db": "ok"}
    return JSONResponse(status_code=503, content={"status": "degraded", "db": "unavailable"})


@app.get(
    "/tasks",
    response_model=List[Task],
    tags=["Tasks"],
    summary="List and Filter Tasks",
    description="Retrieve tasks from PostgreSQL with optional filtering by status (done), search (ILIKE), sorting, and limit/offset pagination."
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status (true/false)"),
    search: Optional[str] = Query(None, description="Search case-insensitive substring in task titles"),
    sort: Optional[str] = Query(None, description="Sort field ('title' or 'id')"),
    order: Optional[str] = Query("asc", description="Sort order ('asc' or 'desc')"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of items to skip from beginning")
):
    return repository.list_tasks(
        done=done,
        search=search,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset
    )


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Get Single Task by ID",
    description="Retrieve a single task from PostgreSQL using a parameterized query."
)
def get_task(task_id: int):
    task = repository.get_task(task_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
        )
    return task


@app.post(
    "/tasks",
    response_model=Task,
    status_code=201,
    tags=["Tasks"],
    summary="Create New Task",
    description="Insert new task into PostgreSQL database with parameterized SQL and return created task."
)
def create_task(task_data: TaskCreate):
    return repository.create_task(title=task_data.title)


@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Update Existing Task",
    description="Update task title and/or done status in PostgreSQL using parameterized SQL."
)
def update_task(task_id: int, task_data: TaskUpdate):
    updated = repository.update_task(
        task_id=task_id,
        title=task_data.title,
        done=task_data.done
    )
    if not updated:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
        )
    return updated


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["Tasks"],
    summary="Delete Task",
    description="Remove a task from PostgreSQL by ID. Returns 204 No Content upon success."
)
def delete_task(task_id: int):
    deleted = repository.delete_task(task_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found", "detail": f"Task {task_id} not found"}
        )
    return Response(status_code=204)


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Analytics & Utilities"],
    summary="Task Statistics",
    description="Computes aggregate metrics directly in PostgreSQL using SELECT COUNT(*) and WHERE clauses."
)
def get_stats():
    return repository.get_stats()


@app.post(
    "/reset",
    tags=["Analytics & Utilities"],
    summary="Reset Seed Tasks",
    description="Atomically resets the PostgreSQL tasks table back to initial 3 seed items."
)
def reset_tasks():
    tasks = repository.reset_tasks()
    return {
        "message": "Tasks successfully reset to initial seed data",
        "tasks": tasks
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
