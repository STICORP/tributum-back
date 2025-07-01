# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Directive

- You should **ALWAYS** ignore any markdown file in the project, especially README.md, when you perform any type of code analysis or discovery.
- You **CANNOT** rely on markdown files because they are absolutely **OUTDATED** and generally just **PLAIN WRONG**.
- If you read or assimilate any markdown file when coding or performing analysis you will pollute your understanding with **WRONG INFORMATION**.

## Project Overview

Tributum is a high-performance financial/tax/payment system built with:
- Python 3.13+ with FastAPI 0.115+
- PostgreSQL with async SQLAlchemy 2.0+
- Clean Architecture (DDD-ready) with clear separation of concerns
- 100% test coverage with comprehensive quality checks

## Essential Commands

### Development
```bash
make install        # Install dependencies and pre-commit hooks
make dev           # Run FastAPI with hot-reload (http://localhost:8000)
make test-fast     # Run tests in parallel (quick feedback)
make all-checks    # Run ALL quality checks before committing
```

### Testing
```bash
make test          # Run all tests with coverage
make test-unit     # Unit tests only
make test-integration  # Integration tests only
pytest tests/unit/test_specific.py::test_function  # Run single test
```

### Code Quality (ALL must pass)
```bash
make format        # Auto-format code with Ruff
make lint          # Linting checks
make type-check    # MyPy strict type checking
make pyright       # Additional type checking
make security      # Security scans (bandit, safety, pip-audit, semgrep)
```

### Database
```bash
make migrate-create MSG="add_user_table"  # Create migration
make migrate-up                           # Apply migrations
make migrate-down                         # Rollback last migration
```

### Docker Development
```bash
make docker-up-dev    # Start with hot-reload
make docker-test      # Run tests in Docker
make docker-migrate   # Run migrations in Docker
```

## Architecture

### Directory Structure
```
src/
├── api/           # HTTP endpoints and request/response models
├── core/          # Shared utilities, exceptions, logging
├── domain/        # Business entities and rules (DDD preparation)
└── infrastructure/# Database, external services, implementations
```

### Request Flow
1. **SecurityHeadersMiddleware** - Adds security headers
2. **RequestContextMiddleware** - Generates correlation ID
3. **RequestLoggingMiddleware** - Logs requests/responses
4. **OpenTelemetry** - Distributed tracing
5. **FastAPI Router** → **Service** → **Repository** → **Database**

### Key Patterns

**Dependency Injection**:
```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    return await service.get_by_id(user_id)
```

**Repository Pattern**:
```python
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> User | None:
        # Implementation
```

**Configuration (Nested with __ delimiter)**:
```bash
DATABASE_CONFIG__POOL_SIZE=10
DATABASE_CONFIG__POOL_TIMEOUT=30
```

## Testing Requirements

- **ALWAYS use pytest-mock**, never unittest.mock
- Tests must maintain 100% coverage
- Use async fixtures for database operations
- Tests run in parallel with worker-specific databases
- Write unit tests in `tests/unit/` and integration tests in `tests/integration/`

## Critical Development Rules

1. **Never bypass checks**: No `# type: ignore`, `# noqa`, or `# pragma: no cover`
2. **Read files completely**: Always read entire files under 2000 lines
3. **Follow existing patterns**: Study similar code before implementing
4. **Test everything**: Write tests for all new features
5. **Use structured logging**: Always use correlation IDs
6. **Handle exceptions properly**: Use the exception hierarchy in `src/core/exceptions.py`

## Common Pitfalls to Avoid

- Don't use synchronous database operations (always `async`)
- Don't forget to add correlation IDs to log messages
- Don't skip pre-commit hooks or quality checks
- Don't add dependencies without updating `pyproject.toml`
- Don't use print() statements - use structured logging
- Don't commit secrets or hardcoded values

## Before Committing

Always run `make all-checks` to ensure:
- Code is formatted (Ruff)
- All linting rules pass
- Type checking passes (MyPy + Pyright)
- All tests pass with 100% coverage
- Security scans pass
- Pre-commit hooks pass
