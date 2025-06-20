# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is a high-performance financial/tax/payment system built with FastAPI, focusing on enterprise-scale operations with strict type safety, comprehensive error handling, and structured observability.

## Common Development Commands

### Core Development
```bash
make install      # Setup dependencies and pre-commit hooks
make dev          # Run FastAPI with auto-reload (127.0.0.1:8000)
make test         # Run all tests with coverage (80% minimum)
make all-checks   # ALL quality checks (required before commit!)
```

### Code Quality
```bash
make format       # Ruff formatting
make lint         # Comprehensive linting (40+ rule sets)
make type-check   # MyPy strict mode (no ignores allowed)
make security     # All security scans (bandit, safety, pip-audit, semgrep)
```

### Testing
```bash
make test-fast              # Parallel execution with pytest-xdist
make test-coverage          # Generate HTML report in htmlcov/
make test-seed SEED=12345   # Debug with specific seed
make test-no-random         # Disable randomization
```

### Running Specific Tests
```bash
# Common test commands
uv run pytest tests/unit/core/test_config.py              # Specific file
uv run pytest tests/unit/core/test_config.py::test_func   # Specific function
uv run pytest -k "test_error" -v                          # Pattern matching
uv run pytest -s tests/unit/core/test_exceptions.py       # With print output
uv run pytest -m unit                                     # Unit tests only
uv run pytest --randomly-seed=12345                       # Debug random failures
uv run pytest -p no:randomly                              # Disable randomization
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

- `/analyze-project` - Project analysis and recommendations
- `/commit` - Smart commits with changelog updates
- `/release` - Version bumping and release creation
- `/readme` - README generation
- `/curate-makefile` - Makefile optimization
- `/enforce-quality` - Quality enforcement
- `/do` - Complex task execution

## Development Standards

### Code Quality Requirements
- **NO** `# type: ignore`, `# noqa`, or `--no-verify`
- **MyPy strict mode** - no Any types allowed
- **80% test coverage minimum**
- **All security scans must pass**
- **Google-style docstrings** for public APIs
- **McCabe complexity ≤ 10**

### Core Patterns
```python
# Exceptions - always with context and severity
raise ValidationError(
    "Invalid email format",
    context={"field": "email", "value": redacted_value},
    severity=Severity.MEDIUM
)

# Logging - structured with context
logger = get_logger(__name__)
with log_context(user_id=123, action="payment") as logger:
    logger.info("Processing payment", amount=100.00)
bind_logger_context(user_id=123, request_id="abc-123")  # Async scope

# Configuration - prefer dependency injection
@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"version": settings.app_version}
```

## Testing Architecture

### Structure
- `tests/unit/` - Fast isolated tests
- `tests/integration/` - Component tests
- `tests/conftest.py` - Shared fixtures
- `tests/fixtures/` - Environment fixtures

### Key Features
- Async support (`pytest-asyncio`)
- Parallel execution (`pytest-xdist`)
- Random ordering (`pytest-randomly`)
- Environment management (`pytest-env`)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`

### Testing Patterns
```python
# Mock with pytest-mock (preferred)
def test_with_mock(mocker):
    mock_func = mocker.patch("src.core.config.get_settings")
    mock_func.return_value = Settings()

# Async testing
@pytest.mark.asyncio
async def test_async_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
```

#### Environment Management with pytest-env
Base test environment configured in pyproject.toml `[tool.pytest_env]`. Use environment fixtures for specific scenarios:

```python
def test_production_behavior(production_env):
    # production_env sets ENVIRONMENT=production, DEBUG=false
    settings = get_settings()
    assert settings.environment == "production"

def test_custom_environment(monkeypatch):
    # Override specific values on base environment
    monkeypatch.setenv("APP_NAME", "Custom Test App")
```

Available fixtures: `production_env`, `development_env`, `staging_env`, `custom_app_env`, `no_docs_env`

Note: `clear_settings_cache` fixture runs automatically (autouse=True).

## Security Architecture

### Security Layers
1. **Input**: Pydantic strict mode validation
2. **Dependencies**: safety, pip-audit scanning
3. **Static Analysis**: bandit, semgrep
4. **Response**: Automatic PII removal
5. **Headers**: HSTS, X-Content-Type-Options, etc.

**Auto-redacted**: password, token, secret, key, authorization, x-api-key, ssn, cpf

## Development Tools

**Package Management**: UV (10x faster than pip) - use `uv run`

**Pre-commit Hooks** (automatic on commit):
1. Ruff formatting/linting (40+ rule sets)
2. MyPy strict type checking
3. Security scans (bandit, safety, semgrep)
4. Dead code detection (vulture)
5. Fast test execution

**Version Management**: `bump-my-version` (syncs pyproject.toml, config.py, VERSION)

## Infrastructure

**Terraform**: `terraform/bootstrap/` (GCP setup), `terraform/environments/` (dev/staging/prod)
**State**: GCS backend

### Environment Variables
```bash
ENVIRONMENT=development|staging|production
LOG_CONFIG__LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
LOG_CONFIG__LOG_FORMAT=console|json
DEBUG=true|false  # Detailed error responses
```

## Performance Optimizations

### Key Strategies
- **JSON**: Default `ORJSONResponse` for 3x faster encoding (handles datetime, UUID, Decimal automatically)
- **Caching**: Settings via `@lru_cache`, structlog logger caching enabled
- **Async**: Pure ASGI middleware only, proper context propagation with contextvars
- **Middleware Order**: security headers → context → logging (order matters!)

### Performance Patterns
```python
# Always use ORJSONResponse
from src.api.utils.responses import ORJSONResponse

@app.get("/data")
async def get_data() -> ORJSONResponse:
    return ORJSONResponse({"data": complex_object})

# Concurrent operations
results = await asyncio.gather(
    fetch_user_data(user_id),
    fetch_payment_data(user_id),
    fetch_tax_data(user_id)
)
```

## Common Error Solutions

**MyPy Errors**:
- Never use `# type: ignore` - find proper types
- Check `[[tool.mypy.overrides]]` for third-party issues
- Use `isinstance()` for type narrowing
- Define complex types in `src/core/types.py`

**Ruff Errors**:
- **C901**: Reduce complexity below 10
- **S101**: No asserts in production code
- **D100-D104**: Add Google-style docstrings
- **PLR0913**: Use Pydantic model for many args

**Imports**:
- Absolute imports from `src/`
- Order: stdlib → third-party → local

## Debugging Tips

### Debug Mode
```bash
export DEBUG=true LOG_CONFIG__LOG_LEVEL=DEBUG LOG_CONFIG__LOG_FORMAT=console
make dev
```

### Key Debug Points
- **Correlation IDs**: Check `X-Correlation-ID` header (UUID4 format)
- **Exception handling**: `src/api/middleware/error_handler.py`
- **Logging**: `src/core/logging.py`
- **Request/Response**: `src/api/middleware/request_logging.py`

### Debugging Failed Tests
```bash
uv run pytest -vvs <file>  # Verbose output with prints
uv run pytest --pdb <file>  # Drop to debugger on failure
uv run pytest -l <file>     # Show local variables
```

## Adding a New Endpoint

1. **Schema** in `src/api/schemas/`:
```python
class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern="^[A-Z]{3}$")
```

2. **Service** in `src/domain/` (business logic)

3. **Route** in `src/api/routes/`:
```python
@router.post("/", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    settings: Annotated[Settings, Depends(get_settings)]
) -> ORJSONResponse:
    result = await process_payment(request)
    return ORJSONResponse(content=result.dict())
```

4. **Register** router in `src/api/main.py`
5. **Test** in `tests/unit/api/routes/`

## Important Notes

- Always use `uv run` for Python commands
- Run `make all-checks` before committing (80%+ coverage required)
- Never manually edit: `uv.lock`, version numbers, pre-commit configs
- Use `bump-my-version` for version management
- Follow existing patterns for middleware/exceptions/logging
