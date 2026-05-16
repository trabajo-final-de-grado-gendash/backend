#!/bin/bash
set -e

echo "Waiting for PostgreSQL database to be ready..."
until pg_isready -h db -U "${DB_USER:-postgres}"; do
  sleep 2
done
echo "PostgreSQL is ready!"

echo "Running Alembic migrations..."
cd /app/api
# Run alembic migrations to setup the genbi_db schema
alembic upgrade head

echo "Running Schema Enhancer..."
export PYTHONPATH=/app/api/src:$PYTHONPATH
python /app/api/src/scripts/run_schema_enhancer.py

echo "Starting the FastAPI application..."
# Move into the api src folder and start uvicorn with hot reload enabled for all local packages
cd /app/api/src
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload \
    --reload-dir /app/api/src \
    --reload-dir /app/decision_agent/src \
    --reload-dir /app/viz_agent/src \
    --reload-dir /app/vanna_agent/src
