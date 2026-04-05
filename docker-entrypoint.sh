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

echo "Starting the FastAPI application..."
# Move into the api src folder and start uvicorn
cd /app/api/src
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
