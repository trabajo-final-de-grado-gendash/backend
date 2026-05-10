#!/bin/bash
set -e

echo "Ensuring the chinook database exists..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE chinook'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chinook')\gexec
EOSQL

echo "Enabling pgvector extension in genbi_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "Creating bigenia schema in chinook database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "chinook" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS bigenia;
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "Loading chinook schema into the chinook database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "chinook" -f /tmp/chinook.sql
echo "Chinook schema loaded successfully!"
