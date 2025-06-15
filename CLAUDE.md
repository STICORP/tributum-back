# CLAUDE.md

## Project Overview
Tributum - Financial/tax/payment system (Python 3.13, FastAPI, Pydantic Settings v2, Terraform/GCP)
GCP Project: tributum-new

## Current Status
- Basic FastAPI app with configuration management
- Exception infrastructure implemented with severity levels and context support
- API error response patterns defined
- Structured logging with structlog (basic setup without correlation IDs)
- Correlation ID generator and request context implemented (UUID4-based, contextvars)
- RequestContextMiddleware for correlation ID propagation
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

# Code quality
uv run vulture .             # Dead code (false positives → vulture_whitelist.py)
uv run interrogate -v .      # Docstring coverage (80% minimum, Google-style)

# Run app
make run

# Terraform (from terraform/ directory)
terraform init
terraform plan
terraform apply
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
│   ├── main.py         # FastAPI app with /info endpoint
│   ├── middleware/
│   │   └── request_context.py  # Correlation ID middleware
│   └── schemas/
│       └── errors.py   # ErrorResponse model
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

# Bind context for async propagation (new)
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
# Prod: JSON format for log aggregation
```

## Notes
Update this file as project grows with new patterns and implementations.
