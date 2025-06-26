# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Directive

You should **ALWAYS** ignore any markdown file in the project, especially README.md, when you perform any type of code analysis or discovery.
You **CANNOT** rely on markdown files because they are absolutely **OUTDATED** and generally just **PLAIN WRONG**.
If you read or assimilate any markdown file when coding or performing analysis you will pollute your understanding with **WRONG INFORMATION**.

## Development Commands

### Running the Application
```bash
make dev              # Run with hot-reload for development
make run              # Run normally
make docker-up-dev    # Run full stack with PostgreSQL in Docker
```

### Code Quality Checks (ALWAYS run before committing)
```bash
make all-checks       # Run all quality checks (lint, format, type-check, etc.)
make lint-fix         # Auto-fix linting issues
make format           # Auto-format code
```

### Testing
```bash
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-coverage    # Generate coverage report (must be ≥80%)
```

### Database Operations
```bash
make migrate-create MSG="describe your change"  # Create new migration
make migrate-up       # Apply migrations
make migrate-down     # Rollback last migration
```

## Architecture Overview

This is a FastAPI application following clean architecture principles with these key layers:

### 1. API Layer (`src/api/`)
- **Entry point**: `src/api/main.py` - FastAPI app configuration
- **Middleware stack** (order matters):
  - Security headers
  - Request context (correlation IDs)
  - Request logging
  - Error handling
- **Schemas**: Pydantic models for request/response validation

### 2. Core Layer (`src/core/`)
- **Configuration**: `config.py` uses Pydantic Settings with environment variables
- **Logging**: Structured logging via structlog
- **Observability**: OpenTelemetry tracing integration
- **Context**: Thread-safe request context propagation

### 3. Infrastructure Layer (`src/infrastructure/`)
- **Repository Pattern**: Generic type-safe repository in `database/repository.py`
- **Database**: SQLAlchemy 2.0+ with async support
- **Session Management**: Singleton pattern without globals
- **Dependency Injection**: FastAPI dependencies for database access

### 4. Testing Strategy
- **Transactional isolation**: Each test runs in a transaction that rolls back
- **Docker PostgreSQL**: Integration tests use real database
- **Fixtures**: Well-organized in `tests/fixtures/`
- **Parallel execution**: Tests can run in parallel with worker-specific databases

## Key Patterns and Conventions

1. **Async-First**: All database operations and endpoints are async
2. **Type Safety**: Extensive type hints, validated by both MyPy and Pyright
3. **Error Handling**: Centralized in middleware, returns structured responses
4. **Logging**: Always use structured logging with context
5. **Configuration**: All settings via environment variables (see `.env.example`)
6. **Repository Pattern**: Inherit from `BaseRepository[T]` for data access
7. **Dependency Injection**: Use FastAPI's `Depends` for dependencies

## Development Workflow

1. **Before starting work**:
   - Run `make install` to ensure dependencies are up to date
   - Check existing tests to understand expected behavior

2. **While developing**:
   - Use `make dev` for hot-reload development
   - Write tests for new functionality
   - Follow existing code patterns and conventions

3. **Before committing**:
   - Run `make all-checks` to ensure code quality
   - Fix any issues with `make lint-fix` and `make format`
   - Ensure tests pass with `make test`
   - Create focused commits with clear messages

4. **Database changes**:
   - Always create migrations with `make migrate-create MSG="..."`
   - Test migrations with up/down before committing
   - Never modify existing migrations

## Important Technical Details

### Database
- Uses PostgreSQL with asyncpg driver
- BigInteger IDs for all tables
- Timezone-aware timestamps (UTC)
- Connection pooling configured in `DatabaseConfig`

### API Response Format
- Uses orjson for fast JSON serialization
- Custom response classes in `api/utils/responses.py`
- Consistent error format with correlation IDs

### Security
- Multiple security scanners integrated (Bandit, pip-audit, Safety, Semgrep)
- Security headers middleware
- Environment-based configuration without hardcoded secrets

### Testing
- Pytest with asyncio support
- 80% coverage requirement
- Random test order by default (use `make test-seed SEED=...` for deterministic order)
- Markers: `@pytest.mark.unit` and `@pytest.mark.integration`

### Environment Variables
- Configuration via Pydantic Settings
- Use double underscore for nested configs (e.g., `LOG__LEVEL=DEBUG`)
- See `.env.example` for all available options

## Common Tasks

### Adding a New Endpoint
1. Define Pydantic schemas in `src/api/schemas/`
2. Create endpoint in appropriate module under `src/api/`
3. Add repository methods if needed in `src/infrastructure/database/`
4. Write unit and integration tests
5. Update API documentation if needed

### Adding a New Database Model
1. Create model in `src/infrastructure/database/models/`
2. Inherit from `BaseModel` for standard fields
3. Create repository inheriting from `BaseRepository[YourModel]`
4. Generate migration: `make migrate-create MSG="add your_table"`
5. Add tests for repository methods

### Debugging
- Set `LOG__LEVEL=DEBUG` for detailed logs
- Use `LOG__SQL=true` to see SQL queries
- Check correlation IDs in logs to trace requests
- OpenTelemetry traces available when configured

## Tool Isolation
Some development tools run in isolated environments via `scripts/tool`:
- Safety (dependency security scanning)
- Semgrep (static analysis)

This prevents dependency conflicts with the main project.
