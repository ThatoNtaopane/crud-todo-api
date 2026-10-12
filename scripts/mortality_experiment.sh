#!/bin/bash
# The Mortality Experiment: Demonstrating Ephemeral Container vs. Persistent Volume

echo "=== Running ephemeral container without volume ==="
docker run --name ephemeral-taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5433:5432 -d postgres:15-alpine
sleep 4

echo "Inserting test task..."
docker exec -i ephemeral-taskdb psql -U postgres -d tasks -c "CREATE TABLE test_data (id serial, val text); INSERT INTO test_data (val) VALUES ('ephemeral'); SELECT * FROM test_data;"

echo "Removing ephemeral container..."
docker rm -f ephemeral-taskdb

echo "Starting fresh container without volume..."
docker run --name ephemeral-taskdb-2 -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5433:5432 -d postgres:15-alpine
sleep 4

echo "Querying table in fresh container (Expect relation does not exist):"
docker exec -i ephemeral-taskdb-2 psql -U postgres -d tasks -c "SELECT * FROM test_data;" || echo "CONFIRMED: Data vanished! Ephemeral storage does not survive container destruction."

docker rm -f ephemeral-taskdb-2
