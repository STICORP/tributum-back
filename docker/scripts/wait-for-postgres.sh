#!/bin/bash
# wait-for-postgres.sh: Script to wait for PostgreSQL to be ready before proceeding
# Used in development and testing to ensure database is available before running tests

set -e

# Get configuration from environment variables with defaults
DATABASE_HOST="${DATABASE_HOST:-localhost}"
DATABASE_PORT="${DATABASE_PORT:-5432}"
DATABASE_USER="${DATABASE_USER:-tributum}"

echo "Waiting for PostgreSQL at $DATABASE_HOST:$DATABASE_PORT..."

# Loop until PostgreSQL is ready
until pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -q
do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up and ready!"
