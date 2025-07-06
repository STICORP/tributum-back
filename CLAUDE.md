# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is a FastAPI-based fiscal intelligence backend using Python 3.13, SQLAlchemy async, PostgreSQL, and UV package manager. The project enforces strict code quality standards with ALL Ruff rules enabled and 100% test coverage requirement.

## Essential Commands

### Development

```bash
# Install dependencies and setup
make install

# Run application
make run          # Production mode
make dev          # Development with hot-reload

# Run specific test patterns
uv run pytest tests/unit/api/test_main.py::test_specific_function
uv run pytest -k "pattern"
```

### Code Quality (MUST run before committing)

```bash
make all-checks   # Run ALL quality checks
make all-fixes    # Auto-fix formatting and imports
make test         # Run all tests with coverage
```

### Database Migrations

```bash
make migrate-create MSG="your migration message"  # Create new migration
make migrate-up                                    # Apply migrations
make migrate-check                                 # Check for pending model changes
```

### Docker Development

```bash
make docker-up-dev     # Start development environment
make docker-logs       # View logs
make docker-shell      # Shell into container
make docker-psql       # Connect to database
```

## Architecture Overview

### Application Structure

```
main.py                    → Uvicorn entry point
src/api/main.py           → FastAPI app factory (create_app())
src/core/config.py        → Pydantic settings with cloud auto-detection
src/core/context.py       → Request correlation ID management via contextvars
src/infrastructure/database/  → Async SQLAlchemy with repository pattern
```

### Request Flow

1. Request → Security headers → Correlation ID generation → Request logging
2. FastAPI route → Dependency injection (DB session) → Repository pattern
3. Response serialization (orjson) → Error handling → OpenTelemetry tracing

### Key Patterns

**Repository Pattern**: Generic `BaseRepository[T]` provides type-safe CRUD operations for any SQLAlchemy model.
**Context Propagation**: Uses Python's `contextvars` to flow correlation IDs through all layers automatically, enabling distributed tracing and log correlation.
**Middleware Pipeline** (executes in reverse order): - SecurityHeadersMiddleware → RequestContextMiddleware → RequestLoggingMiddleware
**Configuration**: Environment variables use `__` delimiter for nesting (e.g., `DATABASE_CONFIG__POOL_SIZE=20`).
**Cloud-Native**: Auto-detects GCP/AWS environments and configures logging/tracing accordingly.

## Testing Patterns

### Test Organization

- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`
- Unit tests mock external dependencies; integration tests use real database
- Each test worker gets its own database for parallel execution

### Database Test Isolation

```python
# Integration tests automatically rollback transactions
async def test_repository_operation(
    test_repository: BaseRepository[TestModel],
    db_session: AsyncSession,
) -> None:
    entity = await test_repository.create({"name": "test"})
    # All changes rolled back after test
```

### Common Fixtures

- `client`: Basic test client
- `client_with_db`: Client with database session injection
- `db_session`: Transactional session with automatic rollback

## Critical Conventions

1. **Type Safety**: All functions must have type hints. Use `Annotated` for FastAPI dependencies.
2. **Error Handling**: Custom exceptions inherit from `TributumException`. Middleware handles consistent error responses.
3. **Database Models**: Inherit from `Base` (includes id, created_at, updated_at fields).
4. **Async Everywhere**: All database operations and I/O must be async.
5. **Logging**: Use `structlog` via core.logging. Correlation IDs are automatically included.
6. **No Direct Imports**: Import from package roots (e.g., `from src.core import config`, not `from src.core.config import Settings`).

## Deployment Notes

- Migrations run separately from app startup (prevents race conditions)
- Use entrypoint.sh for proper container initialization
- Port 8080 for Cloud Run compatibility
- Non-root user (`tributum`) in production containers

## Common Pitfalls

1. **Settings Cache**: Tests automatically clear settings cache. In app code, use `Settings.clear_cache()` if needed.
2. **Request Context**: Always available in request handlers. Access via `RequestContext.get()`.
3. **Database URLs**: Use `postgresql+asyncpg://` for async operations.
4. **Test Isolation**: Never share state between tests. Fixtures handle cleanup automatically.
5. **Import Organization**: Let Ruff handle import sorting. Run `make lint-fix` to auto-fix.

## Performance Considerations

- orjson for fast JSON serialization
- Connection pooling with configurable sizes
- Slow query detection (configurable threshold)
- OpenTelemetry sampling for cost control
