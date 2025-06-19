# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is a high-performance financial/tax/payment system built with FastAPI, focusing on enterprise-scale operations with strict type safety, comprehensive error handling, and structured observability.

## Common Development Commands

### Core Development
- `make install` - Install dependencies and setup pre-commit hooks
- `make dev` - Run FastAPI with auto-reload on 127.0.0.1:8000
- `make run` - Run the application normally
- `make test` - Run all tests with coverage (80% minimum required)
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only

### Code Quality (Required Before Commits)
- `make all-checks` - Run all quality checks (format, lint, type-check, complexity, security, dead-code, docstring)
- `make format` - Format code with Ruff
- `make lint` - Run comprehensive linting with 40+ rule sets
- `make type-check` - Run MyPy in strict mode (no ignores allowed)
- `make complexity-check` - Check McCabe cyclomatic complexity (max 10)
- `make security` - Run all security scans (bandit, safety, pip-audit, semgrep)

### Testing Commands
- `make test-fast` - Run tests in parallel with pytest-xdist
- `make test-coverage` - Generate HTML coverage report in htmlcov/
- `make test-failed` - Re-run only failed tests

### Running Specific Tests
```bash
# Run a specific test file
uv run pytest tests/unit/core/test_config.py

# Run a specific test function
uv run pytest tests/unit/core/test_config.py::test_settings_validation -v

# Run tests matching a pattern
uv run pytest -k "test_error" -v

# Debug a failing test with print statements
uv run pytest -s tests/unit/core/test_exceptions.py

# Run tests with specific markers
uv run pytest -m unit  # Unit tests only
uv run pytest -m integration  # Integration tests only
```

## Architecture Overview

### Layer Structure
```
src/
├── api/              # HTTP/FastAPI layer
│   ├── main.py       # FastAPI app with ORJSONResponse default
│   ├── middleware/   # Pure ASGI middleware stack
│   ├── schemas/      # Pydantic response models
│   └── utils/        # API utilities (ORJSONResponse)
├── core/             # Shared business-agnostic utilities
│   ├── config.py     # Pydantic Settings v2 with nested validation
│   ├── exceptions.py # Severity-based exception hierarchy
│   ├── logging.py    # Structured logging with orjson renderer
│   ├── context.py    # Request context with correlation IDs
│   └── constants.py  # Shared constants
└── domain/           # Business logic (DDD structure prepared)
```

### Key Architectural Patterns

1. **Middleware Stack** (Pure ASGI, not BaseHTTPMiddleware):
   - `RequestContextMiddleware` - Correlation ID management
   - Global exception handlers registered before middleware
   - All middleware uses pure ASGI pattern for performance

2. **Exception System**:
   - Base `TributumError` with severity levels (LOW, MEDIUM, HIGH, CRITICAL)
   - Automatic context capture and fingerprinting for error grouping
   - Specific exceptions: `ValidationError`, `NotFoundError`, `UnauthorizedError`, `BusinessRuleError`
   - Global exception handlers convert to standardized API responses

3. **Logging System**:
   - Structured logging with `structlog` and custom `ORJSONRenderer`
   - Automatic correlation ID injection from request context
   - Console format (dev) vs JSON format (production)
   - Context propagation across async boundaries with contextvars

4. **Configuration**:
   - Pydantic Settings v2 with nested models (e.g., `LogConfig`)
   - Environment variable support with `__` delimiter for nesting
   - Cached settings via `@lru_cache` decorator in `get_settings()`

## Claude Code Commands

The project includes custom Claude Code commands for automation:

- `/analyze-project` - Comprehensive project analysis and recommendations
- `/commit` - Intelligent commit with changelog updates and AI attribution prevention
- `/release` - Automated version bumping and release creation
- `/readme` - Smart README generation with incremental updates
- `/curate-makefile` - Makefile optimization and standardization
- `/enforce-quality` - Strict quality enforcement without bypasses
- `/do` - Execute complex tasks with guidance

## Development Standards

### Code Quality Requirements
- **No Quality Bypasses**: Never use `# type: ignore`, `# noqa`, or `--no-verify`
- **100% Type Safety**: MyPy strict mode with no any types allowed
- **Comprehensive Testing**: 80% minimum coverage enforced in CI
- **Security First**: All security scans must pass (bandit, safety, pip-audit, semgrep)
- **Documentation**: Google-style docstrings required for all public APIs
- **Code Complexity**: McCabe cyclomatic complexity max 10 (C90 rules enforced)

### Exception Handling Patterns
```python
# Use specific exception types with context
raise ValidationError(
    "Invalid email format",
    context={"field": "email", "value": redacted_value},
    severity=Severity.MEDIUM
)

# Exception logging with structured context
log_exception(logger, error, "Operation failed", user_id=123)
```

### Logging Patterns
```python
# Get logger with context
logger = get_logger(__name__)

# Context manager for temporary bindings
with log_context(user_id=123, action="payment") as logger:
    logger.info("Processing payment", amount=100.00)

# Bind context for entire async scope
bind_logger_context(user_id=123, request_id="abc-123")
```

### Configuration Access
```python
# Dependency injection pattern
@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"version": settings.app_version}

# Direct access (cached)
settings = get_settings()
```

## Testing Architecture

### Test Organization
- `tests/unit/` - Fast isolated tests by module
- `tests/integration/` - Component interaction tests
- `tests/conftest.py` - Shared fixtures and test utilities
- `tests/fixtures/` - Environment-specific test fixtures

### Testing Standards
- Async test support with `pytest-asyncio`
- Parallel execution with `pytest-xdist`
- Rich output formatting with `pytest-rich`
- Coverage reports in `htmlcov/` directory
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Environment management with `pytest-env` for consistent test configuration

### Testing Patterns

#### Using pytest-mock (Preferred Approach)
```python
# Clean mocking with pytest-mock
def test_with_mock(mocker):
    mock_func = mocker.patch("src.core.config.get_settings")
    mock_func.return_value = Settings()

# Mock with side effects
def test_error_handling(mocker):
    mocker.patch("src.api.service.process", side_effect=ValueError("Test"))
```

#### Testing Async Code
```python
@pytest.mark.asyncio
async def test_async_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

#### Environment Management with pytest-env
The project uses `pytest-env` to provide consistent test environment configuration:

```python
# Base test environment is configured in pyproject.toml [tool.pytest_env]
# This sets defaults like LOG_CONFIG__LOG_LEVEL = "WARNING" for cleaner test output

# Use environment fixtures for specific test scenarios:
def test_production_behavior(production_env):
    """Test with production environment settings."""
    # production_env fixture automatically sets ENVIRONMENT=production, DEBUG=false, etc.
    settings = get_settings()
    assert settings.environment == "production"
    assert settings.debug is False

def test_custom_environment(monkeypatch):
    """Override specific values on top of base test environment."""
    # Base environment from pytest-env is already applied
    # Use monkeypatch only for test-specific overrides
    monkeypatch.setenv("APP_NAME", "Custom Test App")
    settings = get_settings()
    assert settings.app_name == "Custom Test App"
```

Available environment fixtures:
- `production_env` - Production environment settings
- `development_env` - Development environment settings
- `staging_env` - Staging environment settings
- `custom_app_env` - Custom app name/version for testing overrides
- `no_docs_env` - Disabled API documentation endpoints

Note: The `clear_settings_cache` fixture runs automatically (autouse=True) to ensure each test starts with a fresh settings instance.

#### Testing Exceptions
```python
def test_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Test error", severity=Severity.HIGH)
    assert exc_info.value.severity == Severity.HIGH
    assert "Test error" in str(exc_info.value)
```

## Security Architecture

### Multi-Layer Security
1. **Input Validation**: Pydantic models with strict mode
2. **Dependency Scanning**: safety, pip-audit for known vulnerabilities
3. **Static Analysis**: bandit (AST-based), semgrep (pattern-based)
4. **Response Sanitization**: Automatic PII removal from logs/errors
5. **Security Headers**: HSTS, X-Content-Type-Options, etc.

### Sensitive Data Patterns
Automatically redacted in logs and error responses:
- `password`, `token`, `secret`, `key`
- `authorization`, `x-api-key`, `ssn`, `cpf`

## Development Tools

### Package Management
- **UV Package Manager**: 10x faster than pip, use `uv run` and `uv sync`
- **Isolated Tools**: Some security tools run in isolation via `./scripts/tool`

### Pre-commit Hooks
Comprehensive quality pipeline runs on every commit:
1. Ruff formatting and linting (40+ rule sets including C90 complexity)
2. MyPy strict type checking
3. McCabe complexity check (max complexity 10)
4. Security scanning (bandit, safety, semgrep)
5. Docstring quality validation
6. Dead code detection with vulture
7. Fast test execution

### Version Management
- Semantic versioning with `bump-my-version`
- Automated CHANGELOG.md updates
- Version sync across `pyproject.toml`, `src/core/config.py`, and `VERSION`

## Infrastructure

### Terraform Structure
- `terraform/bootstrap/` - GCP project setup
- `terraform/environments/` - Environment-specific configs (dev/staging/production)
- State management with GCS backend

### Environment Configuration
Key environment variables:
- `ENVIRONMENT` - development/staging/production
- `LOG_CONFIG__LOG_LEVEL` - DEBUG/INFO/WARNING/ERROR/CRITICAL
- `LOG_CONFIG__LOG_FORMAT` - console/json
- `DEBUG` - Enable debug mode and detailed error responses

## Performance Optimizations

### JSON Serialization
- Default `ORJSONResponse` for 3x faster JSON encoding
- Custom `ORJSONRenderer` for structured logs
- Handles datetime, UUID, and custom types automatically

### Caching
- Settings cached with `@lru_cache` for single load per process
- Structlog logger caching enabled

### Async Architecture
- Pure ASGI middleware for optimal performance
- Context variable propagation across async boundaries
- Proper exception handling without BaseHTTPMiddleware issues

## Performance Patterns

### JSON Serialization Best Practices
```python
# Always use ORJSONResponse for API responses
from src.api.utils.responses import ORJSONResponse

@app.get("/data")
async def get_data() -> ORJSONResponse:
    return ORJSONResponse({"data": complex_object})

# ORJSON automatically handles:
# - datetime objects
# - UUID objects
# - Decimal objects
# - Custom types with default parameter
```

### Middleware Performance
- Use pure ASGI middleware (not BaseHTTPMiddleware)
- Middleware order matters: security headers → context → logging
- Avoid blocking operations in middleware
- Use async operations throughout

### Async Best Practices
```python
# Concurrent operations
results = await asyncio.gather(
    fetch_user_data(user_id),
    fetch_payment_data(user_id),
    fetch_tax_data(user_id)
)

# Proper context propagation
from src.core.context import bind_logger_context
bind_logger_context(user_id=user_id, operation="batch_process")
```

## Common Error Patterns and Solutions

### MyPy Strict Mode Errors
- Never use `# type: ignore` - find the proper type annotation
- For third-party library issues, check the `[[tool.mypy.overrides]]` section in pyproject.toml
- Use proper type narrowing with `isinstance()` checks
- For complex types, define them in `src/core/types.py`

### Ruff Linting Errors
- **C901** (complexity): Refactor function to reduce cyclomatic complexity below 10
- **S101** (assert): Use proper exception raising in production code, asserts only in tests
- **D100-D104**: Add missing docstrings in Google style format
- **PLR0913** (too many arguments): Consider using a Pydantic model for parameters

### Import Errors
- Always use absolute imports from `src/`
- Never use relative imports outside test files
- Add `__init__.py` files to all packages
- Follow the import order: stdlib → third-party → local

## Debugging Tips

### Enable Debug Mode
```bash
export DEBUG=true
export LOG_CONFIG__LOG_LEVEL=DEBUG
export LOG_CONFIG__LOG_FORMAT=console
make dev
```

### Trace Correlation IDs
- Check `X-Correlation-ID` header in responses
- Search logs by correlation ID to trace full request flow
- Correlation IDs are UUID4 format
- Every log entry includes the correlation ID automatically

### Common Debug Points
- `src/api/middleware/error_handler.py`: Global exception handling
- `src/core/logging.py`: Log formatting and context
- `src/api/middleware/request_logging.py`: Request/response logging
- `src/core/exceptions.py`: Exception hierarchy and error codes

### Debugging Failed Tests
```bash
# Show full error output
uv run pytest -vvs tests/unit/core/test_exceptions.py

# Run with debugger
uv run pytest --pdb tests/unit/core/test_config.py

# Show local variables on failure
uv run pytest -l tests/unit/api/test_main.py
```

## Adding a New Endpoint Example

1. **Define Pydantic schemas** in `src/api/schemas/`:
```python
# src/api/schemas/payment.py
from decimal import Decimal
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern="^[A-Z]{3}$")
    description: str = Field(min_length=1, max_length=500)

class PaymentResponse(BaseModel):
    id: str
    status: str
    correlation_id: str
```

2. **Create service logic** in `src/domain/` (when implemented):
```python
# src/domain/payment/service.py
async def process_payment(request: PaymentRequest) -> PaymentResult:
    # Business logic here
    pass
```

3. **Create endpoint** in `src/api/routes/`:
```python
# src/api/routes/payment.py
from typing import Annotated
from fastapi import APIRouter, Depends
from src.api.schemas.payment import PaymentRequest, PaymentResponse
from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    settings: Annotated[Settings, Depends(get_settings)]
) -> ORJSONResponse:
    # Process payment
    result = await process_payment(request)
    return ORJSONResponse(
        content=PaymentResponse(
            id=result.id,
            status=result.status,
            correlation_id=RequestContext.get_correlation_id()
        )
    )
```

4. **Register router** in `src/api/main.py`
5. **Add comprehensive tests** in `tests/unit/api/routes/test_payment.py`

## Important Notes

### When Running Commands
- Always use `uv run` prefix for Python commands
- Run `make all-checks` before committing
- Coverage must be 80%+ or builds fail
- Use `make test-fast` for quick feedback during development

### Code Patterns to Follow
- Read existing middleware/exception/logging patterns before implementing new features
- Use dependency injection for settings access
- Always include correlation IDs in error responses
- Follow the exception hierarchy for consistent error handling
- Use structured logging with appropriate context

### Files to Never Modify Manually
- `uv.lock` - Managed by UV package manager
- Version numbers in multiple files - Use `bump-my-version` tool
- Pre-commit hook configurations - Use standard setup
