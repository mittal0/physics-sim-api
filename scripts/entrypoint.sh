#!/bin/bash
set -e

# Entrypoint script for the FastAPI application

echo "Starting Physics Simulation API..."

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z ${DATABASE_HOST:-db} ${DATABASE_PORT:-5432}; do
  sleep 1
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Create artifacts directory
mkdir -p ${ARTIFACTS_PATH:-/app/artifacts}

# Start the application
echo "Starting application..."
exec "$@"