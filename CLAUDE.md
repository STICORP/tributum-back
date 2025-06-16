# CLAUDE.md

## Project Overview
Tributum - Financial/tax/payment system (Python 3.13, FastAPI, Pydantic Settings v2, Terraform/GCP)
GCP Project: tributum-new

## Current Status
- Basic FastAPI app with configuration management
- Exception infrastructure implemented with severity levels and context support
- API error response patterns defined
- Structured logging with structlog with correlation ID support
- Correlation ID generator and request context implemented (UUID4-based, contextvars)
- RequestContextMiddleware for correlation ID propagation (pure ASGI implementation)
- RequestLoggingMiddleware with request/response body logging
- Global exception handlers for all exception types with proper logging
- High-performance JSON serialization with orjson for logs and API responses
- Domain-driven design structure planned (not fully implemented)

## Essential Commands
```bash
# Setup (one-time)
uv run pre-commit install    # Install git hooks

# Quality checks
uv run ruff format .         # Format code
uv run ruff check . --fix    # Lint and fix
uv run mypy .                # Type check
uv run pre-commit run --all-files  # Run all checks

# Security
uv run bandit -r . -c pyproject.toml
uv run safety scan
uv run pip-audit --ignore-vuln PYSEC-2022-42969
uv run semgrep --config=auto .

# Version management
uv run bump-my-version bump patch  # 0.1.0 → 0.1.1
uv run bump-my-version bump minor  # 0.1.1 → 0.2.0
uv run bump-my-version bump major  # 0.2.0 → 1.0.0
```

## CRITICAL DEVELOPMENT RULES

### 1. Re-read This Section MANDATORY
- Before writing ANY code
- Before ANY git operations
- Every 10-15 minutes
- When switching tasks
- **ESPECIALLY: Re-read section 7 before EVER running git commands**

### 2. Write Quality Code From Start
- Read `pyproject.toml` and `.pre-commit-config.yaml` FIRST
- Code must pass ALL checks on first try
- Pre-commit hooks are safety net, not crutch

### 3. NEVER Bypass Checks
**FORBIDDEN:**
- `# type: ignore` - Fix the type issue
- `# noqa` - Fix the lint issue
- `# nosec` - Fix the security issue
- `--no-verify` - Fix the failures
- Disabling rules - Fix the code

**MANDATORY: Task is NOT complete until ALL checks pass. Fix EVERY failure.**

### 4. ALWAYS Read Complete Files
**MANDATORY:**
- NO partial reads under 2000 lines
- NO `limit` or `offset` unless file >2000 lines
- Read ENTIRE file for context
- Partial reads = bugs

### 5. Strategic context7 Usage
- ONLY when needed for specific feature
- Small token limits (1000-3000)
- Never preload docs
- Never exceed 5000 tokens

### 6. Pre-Implementation Analysis MANDATORY
Before ANY code:
1. Search existing patterns: ~~`uv run rg "pattern" --type py`~~ **NOTE: `uv run rg` is timing out - use Grep tool instead**
   - Alternative: Use the Grep tool with pattern and include="*.py"
   - Example: `Grep(pattern="contextvar", include="*.py")`
2. Identify conventions (error handling, naming, testing)
3. Check existing utilities
4. If unclear: ASK, don't assume
5. Generic solutions FORBIDDEN

### 7. Git Commits
- NO AI references ("Claude", "Generated with", etc.)
- Use conventional commit format
- **NEVER commit without explicit user request**
- **AUTHORIZATION RULE: Only commit immediately after /commit slash command in user's LAST prompt**
  - If /commit was used: authorized to run `git commit`
  - If ANY other interaction happened after /commit: authorization expired
  - Must wait for new /commit command
- When /commit is NOT in the last prompt: ONLY stage files and show commit message
- **File Creation Rule**: ALWAYS stage new files immediately after creation
  - Use: `Write(file) && Bash("git add <file>")` pattern
  - Or: `Bash("echo 'content' > file && git add file")`
  - Exception: Temporary/scratch files that will be deleted
  - This prevents "unstaged files detected" errors during commits

### 8. Dependencies
- ALWAYS use latest versions when adding
- Check version: `curl -s https://pypi.org/pypi/PACKAGE/json | grep -o '"version":"[^"]*"' | head -1`

### 9. Minimal Project Note
- Ask for preferences when no patterns exist
- First implementation sets the pattern

## Project Structure (Current)
```
src/
├── api/
│   ├── main.py         # FastAPI app with /info endpoint, uses ORJSONResponse
│   ├── middleware/
│   │   └── request_context.py  # Correlation ID middleware
│   ├── schemas/
│   │   └── errors.py   # ErrorResponse model
│   └── utils/
│       └── responses.py # ORJSONResponse for high-performance JSON
├── core/
│   ├── config.py       # Pydantic Settings
│   ├── context.py      # Correlation ID generation, RequestContext
│   ├── exceptions.py   # Base exceptions, ErrorCode enum
│   ├── error_context.py # Context utilities, sanitization
│   └── logging.py      # Structured logging with structlog
└── domain/            # Empty (planned for business domains)

tests/
├── unit/
└── integration/
```

## Target Architecture (DDD)
- **api/**: HTTP layer (middleware, routing, schemas)
- **core/**: Shared utilities (config, exceptions, logging)
- **domain/**: Business logic per domain (auth/, users/, etc.)
- **infrastructure/**: Technical implementations (database, cache)
Each domain: schemas.py, models.py, repository.py, service.py, exceptions.py

## Core Patterns

### Configuration
```python
from src.core.config import Settings, get_settings
from fastapi import Depends
from typing import Annotated

# In endpoints
def endpoint(settings: Annotated[Settings, Depends(get_settings)]):
    return {"app": settings.app_name}
```

Environment vars: APP_NAME, APP_VERSION, ENVIRONMENT, DEBUG, API_HOST, API_PORT
Nested log config: LOG_CONFIG__LOG_LEVEL, LOG_CONFIG__LOG_FORMAT, LOG_CONFIG__RENDER_JSON_LOGS

### Exceptions
```python
from src.core.exceptions import (
    ErrorCode, Severity, ValidationError, NotFoundError,
    UnauthorizedError, BusinessRuleError
)

# Basic usage
raise ValidationError("Invalid email")
raise NotFoundError("User not found")
raise UnauthorizedError("Invalid token")
raise BusinessRuleError("Insufficient balance")

# With context
raise ValidationError("Invalid email", context={"field": "email", "value": "bad-email"})

# Exception chaining
except ValueError as e:
    raise ValidationError("Invalid format", cause=e)

# Exceptions automatically capture:
# - Stack trace at creation
# - Fingerprint for error grouping
# - Severity level (LOW/MEDIUM/HIGH/CRITICAL)
```

### API Errors
```python
from src.api.schemas.errors import ErrorResponse, ServiceInfo

# Error response includes:
# - error_code, message (required)
# - details, correlation_id, severity, service_info (optional)
# - timestamp (auto-generated with UTC timezone)

# Response fields populated from TributumError attributes
```

## Implementation Workflow
1. Check existing patterns first
2. Use context7 ONLY for specific needs (low tokens)
3. Follow discovered patterns exactly
4. Ask if patterns unclear
5. Verify code consistency

## Known Issues
- PYSEC-2022-42969: py package vulnerability (ignored)
- Safety CLI requires auth

### Request Context & Correlation IDs
```python
from src.core.context import RequestContext, CORRELATION_ID_HEADER

# RequestContextMiddleware automatically handles correlation IDs:
# - Extracts from X-Correlation-ID header or generates UUID4
# - Available via RequestContext.get_correlation_id()
# - Added to response headers
# - Context cleared after request

# Access in handlers/services:
correlation_id = RequestContext.get_correlation_id()
```

### Logging
```python
from src.core.logging import configure_structlog, get_logger, log_context, log_exception

# Configure at app startup
configure_structlog()

# Get logger
logger = get_logger("module_name")  # or get_logger() for auto-name

# Log with structured data
logger.info("user_action", user_id=123, action="login")
logger.error("database_error", error=str(e), query=query)

# Temporary context bindings
with log_context(request_id="abc-123", user_id=456) as logger:
    logger.info("processing request")  # Includes request_id and user_id

# Bind context for async propagation
bind_logger_context(user_id=123, session_id="xyz")  # All subsequent logs include these
logger.info("user action")  # Automatically includes user_id and session_id
clear_logger_context()  # Clean up after request

# Exception logging with full context
try:
    risky_operation()
except TributumError as e:
    log_exception(logger, e, "Operation failed", operation="risky_op")
    # Logs with severity-based level, stack trace, error context, and fingerprint

# Logs include: timestamp, level, logger name, filename, line number, function name
# Correlation ID automatically included when in request context
# Context propagates across async boundaries via contextvars
# Dev: Colored console output
# Prod: JSON format with high-performance orjson serialization
# Performance: 2-10x faster JSON serialization with orjson
```

## Version Management & Release Workflow

Uses [Semantic Versioning](https://semver.org/) with automated changelog tracking.

### Development Workflow
1. **Develop & Commit**: Use `/commit` - automatically updates CHANGELOG.md
2. **Push**: Regular `git push` after commits
3. **Release**: Use `/release` when ready to tag a version

### Automated Changelog
- `/commit` adds entries to `[Unreleased]` section automatically
- Meaningful commits (feat, fix, refactor) tracked
- Test/style commits skipped
- No manual changelog editing needed

### Release Process
```bash
/release  # Analyzes changes, bumps version, creates tag
git push && git push --tags  # Push release
```

Version bump decided by changelog content:
- **PATCH**: Bug fixes, security updates
- **MINOR**: New features (any "Added" entries)
- **MAJOR**: Breaking changes, removals

### Request/Response Logging
```python
from src.api.middleware.request_logging import RequestLoggingMiddleware

# Add middleware with body logging
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=True,      # Log request bodies (default: False)
    log_response_body=True,     # Log response bodies (default: False)
    max_body_size=10*1024,      # Max body size to log (default: 10KB)
)

# Logs include:
# - Method, path, status code, duration
# - Query parameters (sanitized)
# - Request/response headers (sensitive headers redacted)
# - Request/response bodies for JSON/form data (sanitized)
# - Binary data logged as metadata only
# - Large bodies truncated with [TRUNCATED] suffix
# - All sensitive fields automatically sanitized
```

### Global Exception Handling
```python
# Exception handlers are automatically registered in create_app()
# All exceptions are caught and converted to standardized ErrorResponse

# TributumError and subclasses
# - Returns appropriate HTTP status code (400, 401, 404, 422)
# - Includes full context, severity, and correlation ID
# - Stack trace logged but not exposed to clients

# RequestValidationError (FastAPI/Pydantic)
# - Returns 422 with field-level validation errors
# - Groups errors by field name

# HTTPException (Starlette)
# - Converts to our standard error format
# - Maps status codes to appropriate error codes

# Generic Exception
# - Returns 500 Internal Server Error
# - In development: includes exception details
# - In production: hides internal details
# - Always logs full stack trace with structlog

# All error responses include:
# - error_code, message, correlation_id
# - timestamp (UTC), severity, service_info
# - details (sanitized context information)
```

## Notes
Update this file as project grows with new patterns and implementations.
