# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The project uses FastAPI and PostgreSQL and follows Domain-Driven Design (DDD) principles with a clean architecture pattern, emphasizing reliability, observability, and security for financial operations.

## Key Commands

### Development
```bash
make dev                    # Start FastAPI with auto-reload (port 8000)
make install               # Install dependencies and pre-commit hooks
make run                   # Run in production mode
```

### Testing
```bash
make test                  # Run all tests
make test-unit            # Run unit tests only
make test-integration     # Run integration tests only
make test-coverage        # Generate HTML coverage report in htmlcov/
make test-fast            # Run tests in parallel
make test-failed          # Re-run only failed tests
```

### Code Quality (ALWAYS run before committing)
```bash
make format               # Format code with Ruff
make lint-fix            # Fix linting issues
make type-check          # Run MyPy type checking
make pyright             # Run Pyright type checking
make pre-commit          # Run ALL pre-commit checks
```

### Database Migrations
```bash
make migrate-create MSG="description"  # Create new migration
make migrate-up                       # Apply pending migrations
make migrate-down                     # Rollback one migration
make migrate-check                    # Check for pending model changes
```

### Docker Development
```bash
make docker-up-dev       # Start development environment
make docker-down         # Stop all services
make docker-logs         # View logs (SERVICE=api for specific)
make docker-shell        # Shell into API container
make docker-test         # Run tests in Docker
```

### Security Checks
```bash
make security            # Run all security scans
make security-bandit     # Code vulnerability scan
make security-pip-audit  # Dependency vulnerability check
```

## Architecture Overview

The project follows a three-layer clean architecture:

```
src/
├── api/                 # Presentation Layer (FastAPI routes, middleware)
│   ├── main.py         # App factory and route registration
│   ├── middleware/     # Request pipeline (security, logging, context)
│   └── schemas/        # Pydantic models for API contracts
│
├── core/               # Business/Domain Layer
│   ├── config.py       # Configuration management (Pydantic Settings)
│   ├── exceptions.py   # Domain exceptions with severity levels
│   ├── logging.py      # Structured logging with correlation IDs
│   └── observability.py # OpenTelemetry tracing setup
│
└── infrastructure/     # Infrastructure Layer
    └── database/       # PostgreSQL with async SQLAlchemy
        ├── repository.py  # Generic repository pattern
        └── session.py     # Async session management
```

### Key Architectural Patterns

1. **Repository Pattern**: All data access through `BaseRepository` class providing standard CRUD operations
2. **Dependency Injection**: FastAPI's DI for database sessions (`DatabaseSession`) and settings
3. **Middleware Pipeline**: Security headers → Request context → Logging → Error handling
4. **Configuration**: Environment-based with Pydantic Settings (nested config pattern)
5. **Observability**: Correlation IDs throughout request lifecycle, OpenTelemetry tracing

## Important Context

### Project Status
- **Current Phase**: Infrastructure complete, ready for domain implementation
- **No Domain Logic Yet**: The src/domain directory is empty - focus is on infrastructure
- **Financial System**: Built for payment processing, tax calculations, and compliance

### Critical Requirements
1. **Type Safety**: NEVER use `# type: ignore` or `# noqa` - fix the actual issue
2. **Testing**: Maintain 100% coverage, tests required for all new code
3. **Security**: This is a financial system - security is paramount
4. **Precision**: Use Decimal for all monetary calculations
5. **Audit Trail**: All operations must be traceable via correlation IDs

### Development Workflow
1. Always run `make pre-commit` before committing
2. Create migrations for any model changes: `make migrate-create MSG="description"`
3. Use structured logging: `logger = structlog.get_logger()`
4. Add correlation IDs to all operations via `RequestContext`
5. Handle errors with appropriate severity levels (CRITICAL, HIGH, MEDIUM, LOW)

### Testing Strategy
- Unit tests: Mock external dependencies, test business logic
- Integration tests: Test with real database, verify transactions
- Use fixtures from `tests/conftest.py` for consistent test setup
- Run specific test: `pytest tests/path/to/test.py::test_name -v`

### Performance Considerations
- ORJSON for 3x faster JSON serialization (already configured)
- Async/await throughout - never use synchronous database calls
- Connection pooling configured in DatabaseConfig
- Use `select()` with specific columns for large queries

### Security Notes
- All inputs validated via Pydantic schemas
- Security headers middleware active
- Error messages sanitized to prevent information leakage
- Sensitive data should use Pydantic's `SecretStr` type

This is a production-grade financial backend. Code quality, security, and reliability are non-negotiable.
