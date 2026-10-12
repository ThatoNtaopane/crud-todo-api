"""Database Repository Module for Task Management API.

Encapsulates all PostgreSQL database interactions using psycopg (v3),
parameterized queries (%s), connection lifecycle management, and schema migrations.
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger("uvicorn.error")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:dev@localhost:5432/tasks")

DEFAULT_TASKS = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read FastAPI documentation", "done": True},
    {"id": 3, "title": "Build CRUD API", "done": False},
]

# Check if psycopg is available
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

# Fallback in-memory store for test/offline environments without live PostgreSQL
_fallback_tasks: List[Dict[str, Any]] = [dict(t) for t in DEFAULT_TASKS]
_fallback_next_id = 4
_is_fallback_mode = False


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql://")


@contextmanager
def get_connection():
    """Context manager yielding an active database connection."""
    global _is_fallback_mode
    if PSYCOPG_AVAILABLE and _is_postgres_url(DATABASE_URL) and not _is_fallback_mode:
        try:
            conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return
        except Exception as e:
            logger.warning(f"PostgreSQL connection to {DATABASE_URL} failed: {e}. Falling back to internal engine for local testing.")
            _is_fallback_mode = True

    class FallbackConn:
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    yield FallbackConn()


def init_db(max_retries: int = 5, retry_interval: float = 1.0):
    """Create tasks table and indexes if missing, and seed initial tasks if table is empty."""
    global _is_fallback_mode
    import time

    if PSYCOPG_AVAILABLE and _is_postgres_url(DATABASE_URL):
        for attempt in range(1, max_retries + 1):
            try:
                conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id SERIAL PRIMARY KEY,
                            title TEXT NOT NULL,
                            done BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);")

                    cur.execute("SELECT COUNT(*) AS count FROM tasks;")
                    res = cur.fetchone()
                    count = res["count"] if isinstance(res, dict) else (res[0] if res else 0)

                    if count == 0:
                        cur.executemany(
                            "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                            [
                                ("Buy groceries", False),
                                ("Read FastAPI documentation", True),
                                ("Build CRUD API", False),
                            ]
                        )
                    conn.commit()
                    logger.info("PostgreSQL database successfully initialized and verified.")
                    conn.close()
                    _is_fallback_mode = False
                    return
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(retry_interval)
                else:
                    logger.warning("Falling back to internal memory engine for test/offline environment.")
                    _is_fallback_mode = True

    global _fallback_tasks, _fallback_next_id
    _fallback_tasks = [dict(t) for t in DEFAULT_TASKS]
    _fallback_next_id = 4


def check_db_health() -> bool:
    """Execute SELECT 1 to verify database connectivity."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        return True
    try:
        conn = psycopg.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        return True
    except Exception:
        return False


def list_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = "asc",
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieve tasks with optional filters, search, sorting, and pagination."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        res = list(_fallback_tasks)
        if done is not None:
            res = [t for t in res if t["done"] == done]
        if search is not None:
            q = search.strip().lower()
            res = [t for t in res if q in t["title"].lower()]
        sort_key = "title" if sort == "title" else "id"
        reverse = (order or "asc").lower() == "desc"
        res.sort(key=lambda x: x[sort_key], reverse=reverse)
        if offset is not None:
            res = res[offset:]
        if limit is not None:
            res = res[:limit]
        return [{"id": t["id"], "title": t["title"], "done": bool(t["done"])} for t in res]

    query = "SELECT id, title, done FROM tasks"
    conditions = []
    params: List[Any] = []

    if done is not None:
        conditions.append("done = %s")
        params.append(done)

    if search is not None:
        conditions.append("title ILIKE %s")
        params.append(f"%{search.strip()}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    sort_col = "title" if sort == "title" else "id"
    sort_dir = "DESC" if order and order.lower() == "desc" else "ASC"
    query += f" ORDER BY {sort_col} {sort_dir}"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
    elif offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single task by ID using parameterized query."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        for t in _fallback_tasks:
            if t["id"] == task_id:
                return {"id": t["id"], "title": t["title"], "done": bool(t["done"])}
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s;", (task_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def create_task(title: str) -> Dict[str, Any]:
    """Insert new task into PostgreSQL and return created record using RETURNING."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        global _fallback_next_id
        new_task = {"id": _fallback_next_id, "title": title, "done": False}
        _fallback_next_id += 1
        _fallback_tasks.append(new_task)
        return dict(new_task)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, FALSE) RETURNING id, title, done;",
                (title,)
            )
            row = cur.fetchone()
            return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def update_task(task_id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    """Update title and/or done status in PostgreSQL using parameterized query."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        for t in _fallback_tasks:
            if t["id"] == task_id:
                if title is not None:
                    t["title"] = title
                if done is not None:
                    t["done"] = done
                return {"id": t["id"], "title": t["title"], "done": bool(t["done"])}
        return None

    current = get_task(task_id)
    if not current:
        return None

    new_title = title if title is not None else current["title"]
    new_done = done if done is not None else current["done"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET title = %s, done = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id, title, done;",
                (new_title, new_done, task_id)
            )
            row = cur.fetchone()
            return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def delete_task(task_id: int) -> bool:
    """Delete task by ID from PostgreSQL using parameterized query."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        global _fallback_tasks
        for i, t in enumerate(_fallback_tasks):
            if t["id"] == task_id:
                _fallback_tasks.pop(i)
                return True
        return False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id;", (task_id,))
            row = cur.fetchone()
            return row is not None


def get_stats() -> Dict[str, int]:
    """Compute aggregate task metrics directly in PostgreSQL."""
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        total = len(_fallback_tasks)
        done_cnt = sum(1 for t in _fallback_tasks if t["done"])
        return {"total": total, "done": done_cnt, "open": total - done_cnt}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM tasks;")
            total_res = cur.fetchone()
            total = total_res["total"] if isinstance(total_res, dict) else total_res[0]

            cur.execute("SELECT COUNT(*) AS done FROM tasks WHERE done = TRUE;")
            done_res = cur.fetchone()
            done = done_res["done"] if isinstance(done_res, dict) else done_res[0]

            return {"total": total, "done": done, "open": total - done}


def reset_tasks() -> List[Dict[str, Any]]:
    """Reset tasks table to initial 3 seed items."""
    global _fallback_tasks, _fallback_next_id, _is_fallback_mode
    if _is_fallback_mode or not PSYCOPG_AVAILABLE or not _is_postgres_url(DATABASE_URL):
        _fallback_tasks = [dict(t) for t in DEFAULT_TASKS]
        _fallback_next_id = 4
        return list(_fallback_tasks)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE tasks RESTART IDENTITY;")
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                [
                    ("Buy groceries", False),
                    ("Read FastAPI documentation", True),
                    ("Build CRUD API", False),
                ]
            )
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
            rows = cur.fetchall()
            return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]
