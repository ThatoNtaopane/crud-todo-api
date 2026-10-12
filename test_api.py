"""Comprehensive Test Suite for Task Management CRUD API (FastAPI + SQLite3)

Validates all 6 stages, error status codes, validation rules,
parameterized queries, database persistence across restarts,
search, filtering, pagination, and utilities.
"""

import sqlite3
from fastapi.testclient import TestClient
from main import app, reset_tasks, DEFAULT_TASKS, get_db

client = TestClient(app)

def setup_function():
    """Reset tasks SQLite database before each test run."""
    reset_tasks()

def test_root_endpoint():
    setup_function()
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Task API"
    assert data["version"] == "2.0"
    assert "/tasks" in data["endpoints"]

def test_health_endpoint():
    setup_function()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_get_all_tasks():
    setup_function()
    resp = client.get("/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[0]["title"] == "Buy groceries"
    assert data[0]["done"] is False

def test_get_single_task_success():
    setup_function()
    resp = client.get("/tasks/1")
    assert resp.status_code == 200
    assert resp.json() == {"id": 1, "title": "Buy groceries", "done": False}

def test_get_single_task_not_found():
    setup_function()
    resp = client.get("/tasks/99")
    assert resp.status_code == 404
    assert resp.json()["error"] == "Task 99 not found"

def test_create_task_success():
    setup_function()
    payload = {"title": "Buy milk"}
    resp = client.post("/tasks", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == 4
    assert created["title"] == "Buy milk"
    assert created["done"] is False

    # Verify task was persisted to SQLite
    list_resp = client.get("/tasks")
    assert len(list_resp.json()) == 4
    assert any(t["title"] == "Buy milk" for t in list_resp.json())

def test_create_task_validation_missing_title():
    setup_function()
    resp = client.post("/tasks", json={})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_create_task_validation_empty_title():
    setup_function()
    resp = client.post("/tasks", json={"title": "   "})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_update_task_title():
    setup_function()
    resp = client.put("/tasks/1", json={"title": "Buy organic groceries"})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["id"] == 1
    assert updated["title"] == "Buy organic groceries"
    assert updated["done"] is False

def test_update_task_done_status():
    setup_function()
    resp = client.put("/tasks/1", json={"done": True})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["done"] is True
    assert updated["title"] == "Buy groceries"

def test_update_task_both_fields():
    setup_function()
    resp = client.put("/tasks/3", json={"title": "Deploy CRUD API to production", "done": True})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "Deploy CRUD API to production"
    assert updated["done"] is True

def test_update_task_empty_body():
    setup_function()
    resp = client.put("/tasks/1", json={})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_update_task_empty_title():
    setup_function()
    resp = client.put("/tasks/1", json={"title": ""})
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_update_task_not_found():
    setup_function()
    resp = client.put("/tasks/999", json={"title": "Non-existent task"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "Task 999 not found"

def test_delete_task_success():
    setup_function()
    resp = client.delete("/tasks/2")
    assert resp.status_code == 204
    assert resp.content == b""

    # Confirm deletion via GET
    get_resp = client.get("/tasks/2")
    assert get_resp.status_code == 404
    assert get_resp.json()["error"] == "Task 2 not found"

    # Confirm total tasks reduced to 2 in SQLite
    list_resp = client.get("/tasks")
    assert len(list_resp.json()) == 2

def test_delete_task_not_found():
    setup_function()
    resp = client.delete("/tasks/999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "Task 999 not found"

def test_query_filter_done():
    setup_function()
    # Only completed
    resp_done = client.get("/tasks?done=true")
    assert resp_done.status_code == 200
    assert len(resp_done.json()) == 1
    assert resp_done.json()[0]["id"] == 2

    # Only open
    resp_open = client.get("/tasks?done=false")
    assert resp_open.status_code == 200
    assert len(resp_open.json()) == 2
    assert all(t["done"] is False for t in resp_open.json())

def test_search_filter():
    setup_function()
    resp = client.get("/tasks?search=documentation")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert "FastAPI documentation" in resp.json()[0]["title"]

def test_pagination():
    setup_function()
    # Offset 1, limit 1
    resp = client.get("/tasks?limit=1&offset=1")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == 2

def test_stats():
    setup_function()
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"total": 3, "done": 1, "open": 2}

def test_reset():
    setup_function()
    # Add a task
    client.post("/tasks", json={"title": "Temporary Task"})
    assert len(client.get("/tasks").json()) == 4

    # Call reset
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert len(client.get("/tasks").json()) == 3

def test_docs_and_openapi():
    setup_function()
    resp_docs = client.get("/docs")
    assert resp_docs.status_code == 200
    resp_spec = client.get("/openapi.json")
    assert resp_spec.status_code == 200
    assert "openapi" in resp_spec.json()

def test_sqlite_persistence_across_reconnect():
    """Verify data outlives process/connections in tasks.db."""
    setup_function()
    # 1. Add persistent item
    client.post("/tasks", json={"title": "Persistent Database Item"})
    
    # 2. Query directly via fresh SQLite connection
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tasks WHERE title = ?;", ("Persistent Database Item",))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["title"] == "Persistent Database Item"

def test_sql_injection_safety():
    """Verify parameterized queries prevent SQL injection."""
    setup_function()
    # Attempt SQL injection via search parameter
    injection_search = "' OR '1'='1"
    resp = client.get(f"/tasks?search={injection_search}")
    assert resp.status_code == 200
    # Parameterized query treats it as literal string, so 0 matching tasks
    assert len(resp.json()) == 0

if __name__ == "__main__":
    print("Running automated test suite for SQLite CRUD API...")
    test_root_endpoint()
    test_health_endpoint()
    test_get_all_tasks()
    test_get_single_task_success()
    test_get_single_task_not_found()
    test_create_task_success()
    test_create_task_validation_missing_title()
    test_create_task_validation_empty_title()
    test_update_task_title()
    test_update_task_done_status()
    test_update_task_both_fields()
    test_update_task_empty_body()
    test_update_task_empty_title()
    test_update_task_not_found()
    test_delete_task_success()
    test_delete_task_not_found()
    test_query_filter_done()
    test_search_filter()
    test_pagination()
    test_stats()
    test_reset()
    test_docs_and_openapi()
    test_sqlite_persistence_across_reconnect()
    test_sql_injection_safety()
    print("All 24 test cases passed successfully!")
