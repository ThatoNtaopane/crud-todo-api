"""AI Generated Task API (Initial Version - Quarantine)"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Task API", version="1.0.0")

# In-memory storage
tasks_db = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read FastAPI documentation", "done": True},
    {"id": 3, "title": "Build CRUD API", "done": False},
]

class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool

@app.get("/")
def get_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

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
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate):
    if not task_in.title or not task_in.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    next_id = max([t["id"] for t in tasks_db], default=0) + 1
    new_task = {
        "id": next_id,
        "title": task_in.title.strip(),
        "done": False
    }
    tasks_db.append(new_task)
    return new_task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_in: TaskUpdate):
    for task in tasks_db:
        if task["id"] == task_id:
            if task_in.title is not None:
                if not task_in.title.strip():
                    raise HTTPException(status_code=400, detail="Title cannot be empty")
                task["title"] = task_in.title.strip()
            if task_in.done is not None:
                task["done"] = task_in.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for idx, task in enumerate(tasks_db):
        if task["id"] == task_id:
            tasks_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
