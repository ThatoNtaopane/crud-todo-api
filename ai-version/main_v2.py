"""AI Rematch Version (Generated from improved specification prompt)"""

from typing import Optional, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, validator, root_validator

app = FastAPI(title="Task Management API", version="1.0.0")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Invalid request body"
    return JSONResponse(status_code=400, content={"error": f"Validation error: {msg}"})

tasks_db = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read FastAPI documentation", "done": True},
    {"id": 3, "title": "Build CRUD API", "done": False},
]

class TaskCreate(BaseModel):
    title: str

    @validator("title")
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title is required and cannot be empty")
        return v.strip()

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @validator("title")
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else v

    @root_validator
    def check_non_empty(cls, values):
        if values.get("title") is None and values.get("done") is None:
            raise ValueError("Empty request body: at least one field ('title' or 'done') must be provided")
        return values

class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool

@app.get("/")
def get_root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks():
    return tasks_db

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(task_in: TaskCreate):
    next_id = max([t["id"] for t in tasks_db], default=0) + 1
    new_task = {"id": next_id, "title": task_in.title, "done": False}
    tasks_db.append(new_task)
    return new_task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_in: TaskUpdate):
    for task in tasks_db:
        if task["id"] == task_id:
            if task_in.title is not None:
                task["title"] = task_in.title
            if task_in.done is not None:
                task["done"] = task_in.done
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for idx, task in enumerate(tasks_db):
        if task["id"] == task_id:
            tasks_db.pop(idx)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
