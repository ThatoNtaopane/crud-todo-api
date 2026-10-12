"""AI-Generated Initial Implementation (Quarantined)"""
import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="Task API AI Version")

# Note: AI used a fallback with a hardcoded password string instead of strictly requiring .env
DB_URL = os.getenv("DATABASE_URL", "postgres://postgres:password123@localhost:5432/tasks")

class TaskSchema(BaseModel):
    id: Optional[int]
    title: str
    done: bool = False

def get_db():
    # Note: AI does not use connection pool or context manager, opens connection per-request
    return psycopg.connect(DB_URL, row_factory=dict_row)

@app.on_event("startup")
def startup():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN DEFAULT FALSE
            );
        """)
        cur.execute("SELECT COUNT(*) FROM tasks;")
        if cur.fetchone()["count"] == 0:
            cur.execute("INSERT INTO tasks (title, done) VALUES ('Task 1', false), ('Task 2', true), ('Task 3', false);")
    conn.commit()
    conn.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks")
def list_tasks():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM tasks ORDER BY id ASC;")
        rows = cur.fetchall()
    conn.close()
    return rows

@app.post("/tasks", status_code=201)
def create_task(task: TaskSchema):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Invalid title")
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *;", (task.title, task.done))
        new_row = cur.fetchone()
    conn.commit()
    conn.close()
    return new_row

@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    conn = get_db()
    with conn.cursor() as cur:
        # Note: Flaw found in review - AI formatted string instead of parameterized query for id
        cur.execute(f"DELETE FROM tasks WHERE id = {id}")
    conn.commit()
    conn.close()
    return Response(status_code=204)
