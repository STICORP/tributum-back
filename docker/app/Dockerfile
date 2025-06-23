# Production Dockerfile for Tributum
# Multi-stage build for minimal and secure runtime image

# Build stage - Install dependencies
FROM python:3.13-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev dependencies)
# UV will create a virtual environment in .venv
RUN uv sync --frozen --no-dev

# Runtime stage - Minimal production image
FROM python:3.13-slim

# Install runtime dependencies only
# libpq-dev is needed for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with specific UID for consistency
RUN useradd -m -u 1000 -s /bin/bash tributum

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=tributum:tributum /build/.venv /app/.venv

# Copy application code
COPY --chown=tributum:tributum . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs && chown tributum:tributum /app/logs

# Switch to non-root user
USER tributum

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Force production environment
    ENVIRONMENT=production \
    # Disable debug mode
    DEBUG=false \
    # Default API settings for container environments
    API_HOST=0.0.0.0 \
    # Port will be overridden by Cloud Run's PORT env var
    API_PORT=8080

# Expose port (Cloud Run default)
EXPOSE 8080

# Health check (respects configured port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${API_PORT:-8080}/health || exit 1

# Set entrypoint
ENTRYPOINT ["/app/docker/scripts/entrypoint.sh"]

# Default command (uses main.py which respects environment variables)
CMD ["python", "main.py"]
