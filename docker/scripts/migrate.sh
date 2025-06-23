#!/bin/bash
# migrate.sh: Database migration script for Tributum
# This script should be run separately from the main application
# For example: as a Cloud Build step, Kubernetes Job, or manual execution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[MIGRATE]${NC} $1"
}

error() {
    echo -e "${RED}[MIGRATE ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[MIGRATE WARNING]${NC} $1"
}

# Check if DATABASE_CONFIG__DATABASE_URL is set
if [ -z "$DATABASE_CONFIG__DATABASE_URL" ]; then
    error "DATABASE_CONFIG__DATABASE_URL is not set"
    exit 1
fi

# Extract database connection parameters for verification
DB_URL="$DATABASE_CONFIG__DATABASE_URL"
DB_URL_NO_PROTO="${DB_URL#postgresql+asyncpg://}"
DB_URL_NO_PROTO="${DB_URL_NO_PROTO#postgresql://}"

if [[ "$DB_URL_NO_PROTO" =~ ^([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)$ ]]; then
    DATABASE_HOST="${BASH_REMATCH[3]}"
    DATABASE_PORT="${BASH_REMATCH[4]}"
    DATABASE_NAME="${BASH_REMATCH[5]}"
    log "Database: ${DATABASE_NAME} at ${DATABASE_HOST}:${DATABASE_PORT}"
else
    error "Unable to parse database URL format"
    exit 1
fi

# Check if alembic is available
if ! python -m alembic --help &> /dev/null; then
    error "Alembic is not available. Ensure it's installed in the environment."
    exit 1
fi

# Check current migration status
log "Checking current migration status..."
if python -m alembic current; then
    log "Current migration status retrieved successfully"
else
    warning "Could not retrieve current migration status (database might be empty)"
fi

# Run migrations
log "Running database migrations..."
if python -m alembic upgrade head; then
    log "Database migrations completed successfully!"

    # Show the new current version
    log "New migration status:"
    python -m alembic current
else
    error "Database migrations failed!"
    exit 1
fi

log "Migration process completed"
