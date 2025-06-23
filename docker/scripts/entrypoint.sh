#!/bin/bash
# entrypoint.sh: Docker entrypoint script for Tributum
# Minimal entrypoint that lets the application handle database connections

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[ENTRYPOINT]${NC} $1"
}

error() {
    echo -e "${RED}[ENTRYPOINT ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[ENTRYPOINT WARNING]${NC} $1"
}

# Verify DATABASE_CONFIG__DATABASE_URL is set
if [ -z "$DATABASE_CONFIG__DATABASE_URL" ]; then
    error "DATABASE_CONFIG__DATABASE_URL is not set"
    exit 1
fi

# Note about database connections:
# The application uses SQLAlchemy with pool_pre_ping=True which automatically
# tests connections before use. This is more reliable than waiting at startup
# because it handles transient network issues throughout the application lifecycle.

# Note about migrations:
# Database migrations should be run as a separate process (e.g., Cloud Build step,
# Kubernetes Job, or manual execution) to avoid race conditions with multiple instances.
# Use: docker run <image> bash /app/docker/scripts/migrate.sh

# Execute the main command
log "Starting application with command: $*"
exec "$@"
