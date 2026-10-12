-- Query Optimization & Indexing Benchmark in PostgreSQL
-- Compare query planning before and after indexing the 'done' column.

-- 1. Explain analyze query filtering on 'done'
EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = TRUE;

-- 2. Explain analyze query searching task titles
EXPLAIN ANALYZE SELECT * FROM tasks WHERE title ILIKE '%fastapi%';

-- 3. Verify index usage in PostgreSQL catalog
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'tasks';
