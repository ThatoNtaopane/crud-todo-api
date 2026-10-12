from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator, root_validator

app = FastAPI(
    title="Task Management API",
    description="A lightweight in-memory CRUD API for managing to-do tasks, built with FastAPI and OpenAPI/Swagger UI.",
    version="1.0.0",
    openapi_tags=[
        {"name": "System", "description": "API root discovery and health check endpoints"},
        {"name": "Tasks", "description": "Core CRUD operations and querying for tasks"},
        {"name": "Analytics & Utilities", "description": "Computed metrics and demo seed controls"},
    ]
)

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

# In-memory "database" initialized from seed
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
    summary="API Root Information",
    description="Returns API service information, version number, and main endpoint locations."
)
def get_root():
    return {
        "name": "Task API",
        "version": "1.0",
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
    description="Retrieve tasks with optional filtering by completion status (done), substring search, and limit/offset pagination."
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status (true/false)"),
    search: Optional[str] = Query(None, description="Search case-insensitive substring in task titles"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of items to return"),
    offset: Optional[int] = Query(None, ge=0, description="Number of items to skip from beginning")
):
    results = tasks

    if done is not None:
        results = [t for t in results if t["done"] == done]

    if search is not None:
        q = search.strip().lower()
        results = [t for t in results if q in t["title"].lower()]

    if offset is not None:
        results = results[offset:]

    if limit is not None:
        results = results[:limit]

    return results

@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Get Single Task by ID",
    description="Retrieve detailed information for a specific task using its unique integer ID."
)
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

@app.post(
    "/tasks",
    response_model=Task,
    status_code=201,
    tags=["Tasks"],
    summary="Create New Task",
    description="Add a new task to the in-memory list with automated ID generation and input validation."
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
    summary="Update Existing Task",
    description="Update the title and/or completion status of an existing task by ID."
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
    summary="Delete Task",
    description="Remove a task from the list by its ID. Returns 204 No Content upon success."
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
    summary="Task Statistics",
    description="Computes aggregate metrics for tasks in memory (total, done, open counts)."
)
def get_stats():
    total_count = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    open_count = total_count - done_count
    return {"total": total_count, "done": done_count, "open": open_count}

@app.post(
    "/reset",
    tags=["Analytics & Utilities"],
    summary="Reset Seed Tasks",
    description="Restores the in-memory tasks list back to the initial 3 example tasks."
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
