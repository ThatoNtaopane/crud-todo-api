-- FlyRank Week 3 Assignment A2: Stage 4 - Manual SQL Exploration
-- Run directly against tasks.db (e.g., via DB Browser for SQLite or sqlite3 CLI)

-- 1. List every task in the database
SELECT * FROM tasks;

-- 2. Filter for only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- 3. Count total number of tasks
SELECT COUNT(*) FROM tasks;

-- 4. Bulk update: mark every task as completed
UPDATE tasks SET done = 1;

-- 5. Bulk deletion: delete all completed tasks
DELETE FROM tasks WHERE done = 1;
