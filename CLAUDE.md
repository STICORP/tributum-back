# CLAUDE.md

## Project Overview
Tributum - Financial/tax/payment system (Python 3.13, FastAPI, Pydantic Settings v2, Terraform/GCP)
GCP Project: tributum-new

## Current Status
- Basic FastAPI app with configuration management
- Exception infrastructure implemented with severity levels and context support
- API error response patterns defined
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
- Before ANY commits
- Every 10-15 minutes
- When switching tasks

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
1. Search existing patterns: `uv run rg "pattern" --type py`
2. Identify conventions (error handling, naming, testing)
3. Check existing utilities
4. If unclear: ASK, don't assume
5. Generic solutions FORBIDDEN

### 7. Git Commits
- NO AI references ("Claude", "Generated with", etc.)
- Use conventional commit format

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
│   └── schemas/
│       └── errors.py   # ErrorResponse model
├── core/
│   ├── config.py       # Pydantic Settings
│   └── exceptions.py   # Base exceptions, ErrorCode enum
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

Environment vars: APP_NAME, APP_VERSION, ENVIRONMENT, DEBUG, API_HOST, API_PORT, LOG_LEVEL

### Exceptions
```python
from src.core.exceptions import (
    ErrorCode, Severity, ValidationError, NotFoundError,
    UnauthorizedError, BusinessRuleError
)

# Use specialized exceptions
raise ValidationError("Invalid email")
raise NotFoundError("User not found")
raise ValidationError("Invalid email", context={"field": "email"})

# Exception chaining
except ValueError as e:
    raise ValidationError("Invalid format", cause=e)

# Severity: LOW (validation/not found), MEDIUM (business rules), HIGH (auth), CRITICAL (system)
# Error codes: INTERNAL_ERROR, VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED
```

### API Errors
```python
from src.api.schemas.errors import ErrorResponse, ServiceInfo

# Standardized error responses
ErrorResponse(
    error_code="VALIDATION_ERROR",
    message="Invalid input",
    details={"field": "error"},  # Optional
    correlation_id="...",        # Optional
    timestamp=datetime.now(UTC), # Auto-generated with timezone
    severity="WARNING",          # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL
    service_info=ServiceInfo(    # Optional: service metadata
        name="Tributum",
        version="0.1.0",
        environment="production"
    )
)
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

## Notes
Update this file as project grows with new patterns and implementations.
