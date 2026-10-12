"""AI Rematch Implementation (v2) - Hardened against Code Review Findings"""
import os
import time
from typing import Optional, List
from fastapi import FastAPI, Request, Query, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="Task Management API (AI Rematch v2)")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required and cannot be empty.")

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Validation error: invalid request body"})

def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

@app.on_event("startup")
def startup():
    for attempt in range(5):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id SERIAL PRIMARY KEY,
                            title TEXT NOT NULL,
                            done BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
                    """)
                    cur.execute("SELECT COUNT(*) AS count FROM tasks;")
                    if cur.fetchone()["count"] == 0:
                        cur.executemany(
                            "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                            [("Buy groceries", False), ("Read FastAPI documentation", True), ("Build CRUD API", False)]
                        )
            return
        except Exception:
            time.sleep(1.5)

@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ok", "db": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "db": "error"})
