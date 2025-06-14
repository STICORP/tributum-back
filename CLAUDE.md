# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is currently an empty project in its initial setup phase. The project name suggests it may be related to financial, tax, or payment systems.

## Project Status

- **Current State**: Python project initialized with uv, basic FastAPI application with configuration management implemented
- **Technology Stack**:
  - Backend: Python 3.13 with FastAPI
  - Configuration: Pydantic Settings v2
  - Infrastructure: Terraform with GCP
- **Build System**: uv (Python package manager)

## Development Setup

### Python Development

#### Linting and Formatting

The project uses Ruff for code quality:

```bash
# Run linter
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check formatting without making changes
uv run ruff format --check .
```

#### Type Checking

The project uses mypy for static type checking with strict settings:

```bash
# Run type checking on all files
uv run mypy .

# Run type checking on specific file/directory
uv run mypy src/

# Run with more verbose output
uv run mypy . --show-error-codes

# Ignore specific error codes temporarily
uv run mypy . --ignore-missing-imports
```

Type checking configuration:
- Strict mode enabled for all project code (`tributum.*`)
- Permissive mode for third-party libraries
- More relaxed rules for test files

#### Pre-commit Hooks

The project uses pre-commit to automatically run checks before commits:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run pre-commit on all files manually
uv run pre-commit run --all-files

# Skip pre-commit temporarily
git commit --no-verify
```

Pre-commit runs:
- Basic file checks (trailing whitespace, file endings, YAML/TOML/JSON validation)
- Python syntax verification (AST check)
- Debug statement detection
- Docstring position verification
- Test file naming conventions
- Ruff linting and formatting
- Mypy type checking
- Bandit security scanning
- Safety dependency vulnerability checks
- pip-audit vulnerability scanning
- Semgrep advanced static analysis

#### Security Scanning

The project uses multiple security tools to ensure code and dependency safety:

```bash
# Run Bandit security scan
uv run bandit -r . -c pyproject.toml

# Check for vulnerable dependencies (deprecated, use scan instead)
uv run safety scan

# Audit dependencies (more comprehensive)
# Note: Currently ignoring PYSEC-2022-42969 (py package vulnerability from interrogate)
uv run pip-audit --ignore-vuln PYSEC-2022-42969

# Run Semgrep for advanced security analysis
uv run semgrep --config=auto .

# Run all security checks at once
uv run bandit -r . && uv run safety scan && uv run pip-audit --ignore-vuln PYSEC-2022-42969
```

Security tools:
- **Bandit**: Finds common security issues in Python code (hardcoded passwords, SQL injection, etc.)
- **Safety**: Checks dependencies against known vulnerabilities database
- **pip-audit**: Audits packages against OSV vulnerability database
- **Semgrep**: Static analysis for security patterns and anti-patterns

#### Code Quality Tools

The project uses additional tools to maintain high code quality:

```bash
# Check for dead code
uv run vulture .

# Generate dead code report
uv run vulture . --sort-by-size > dead-code-report.txt

# Check docstring coverage
uv run interrogate -v .

# Generate docstring badge
uv run interrogate --generate-badge . --badge-format svg
```

Code quality tools:
- **Vulture**: Detects unused code (imports, variables, functions, classes)
- **Interrogate**: Measures docstring coverage to ensure code is well-documented

##### Dead Code Detection Policy

When vulture reports potentially unused code:
1. **Verify the finding** - Some code may be used dynamically (e.g., FastAPI routes, pytest fixtures)
2. **If truly unused** - Remove the code to keep the codebase clean
3. **If false positive** - Add to `vulture_whitelist.py` with a comment explaining why it's needed
4. **Regular cleanup** - Run `make dead-code` periodically to prevent accumulation

##### Docstring Coverage Policy

Maintain high docstring coverage (80% minimum) by:
1. **Document all public APIs** - Functions, classes, and methods exposed to users
2. **Use Google-style docstrings** - Consistent with project's Ruff configuration
3. **Include examples** - For complex functions, include usage examples
4. **Run checks regularly** - Use `make docstring-coverage` before commits

### Configuration Management

The project uses Pydantic Settings v2 for centralized configuration management:

#### Configuration Structure

- **Location**: `src/core/config.py`
- **Settings Class**: Manages all application configuration with type safety and validation
- **Environment Variables**: Loaded from `.env` file and system environment
- **Dependency Injection**: Integrated with FastAPI using `Depends(get_settings)`

#### Configuration Variables

```bash
# Application settings
APP_NAME=Tributum                      # Application name
APP_VERSION=0.1.0                       # Application version
ENVIRONMENT=development                 # Environment (development/staging/production)
DEBUG=false                             # Debug mode (enables auto-reload)

# API settings
API_HOST=127.0.0.1                      # API host (use 127.0.0.1 for security)
API_PORT=8000                           # API port
DOCS_URL=/docs                          # OpenAPI documentation URL (set empty to disable)
REDOC_URL=/redoc                        # ReDoc documentation URL (set empty to disable)
OPENAPI_URL=/openapi.json               # OpenAPI schema URL (set empty to disable)

# Logging
LOG_LEVEL=INFO                          # Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
```

#### Usage in Code

```python
# In FastAPI endpoints
from typing import Annotated
from fastapi import Depends
from src.core.config import Settings, get_settings

@app.get("/info")
def get_info(settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }

# Direct usage (for startup/CLI)
from src.core.config import get_settings

settings = get_settings()
uvicorn.run(
    app,
    host=settings.api_host,
    port=settings.api_port,
)
```

#### Development Commands

```bash
# Run the application
make run                # Uses configuration from .env and environment

# Run with custom settings
API_PORT=8080 make run  # Override specific settings

# View current configuration (through API)
curl http://localhost:8000/info
```

### Infrastructure (Terraform)

- **GCP Project**: tributum-new
- **Service Account Key**: Located at `.keys/tributum-new-infrastructure-as-code-ce93f5144008.json`
- **Terraform State**: Stored remotely in GCS bucket `tributum-new-terraform-state`
- **Directory Structure**:
  - `terraform/` - Main infrastructure configuration
  - `terraform/bootstrap/` - Bootstrap configuration for state bucket (one-time setup)

### Terraform Commands

```bash
# Initialize Terraform (from terraform/ directory)
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply
```

**Note**: The service account key path is hardcoded in both the backend configuration and as a variable. This is necessary because Terraform backends cannot use variables.

## Development Guidelines

### MANDATORY: Re-read This Section Before Every Task

**YOU MUST re-read the Development Guidelines section of CLAUDE.md:**
- Before writing ANY code
- Before making ANY commits
- Before implementing ANY feature
- After every 10-15 minutes of work
- Whenever switching between different types of tasks

This is not optional. Your track record shows you forget these guidelines during long sessions. The only solution is frequent re-reading to keep them fresh in memory.

### FUNDAMENTAL PRINCIPLE: Write Quality Code From the Start

**PRIMARY RULE**: Write code that conforms to ALL configured quality standards from the beginning. Pre-commit hooks are a safety net, not a crutch.

Before writing ANY code:
1. **Read the project's configuration files** to understand the quality standards:
   - `pyproject.toml` - Ruff, mypy, and other tool configurations
   - `.pre-commit-config.yaml` - All configured checks
   - Any other tool-specific configs
2. **Write code that conforms to these configurations** from the start
3. **Aim for zero pre-commit failures** - Multiple commit attempts indicate poor attention to quality

The standards are already defined in the configuration files. Read them, understand them, and follow them. Don't guess or assume - the project tells you exactly what it expects.

### FUNDAMENTAL PRINCIPLE: Never Bypass Quality Checks

**ABSOLUTE RULE**: If ANY configured check fails (pre-commit hook, linter, type checker, security scanner, etc.), you MUST fix the root cause. NEVER bypass, ignore, or disable the check.

Examples of what NOT to do:
- `# type: ignore` - NO! Fix the type checking configuration
- `# noqa` - NO! Fix the linting issue
- `# nosec` - NO! Fix the security concern
- `--no-verify` - NO! Fix the pre-commit failures
- Disabling rules in config - NO! Fix the code to comply

**The Correct Approach**:
1. Understand WHY the check is failing
2. Research the proper solution
3. Fix the root cause (configuration, code, or dependencies)
4. If you can't fix it, ASK for guidance - don't bypass

This applies to ALL checks: mypy, ruff, bandit, safety, pip-audit, semgrep, or any future tool. These checks exist to maintain code quality, security, and consistency. Bypassing them defeats their purpose and compromises the project's standards.

### CRITICAL: Library Documentation Research

**MANDATORY**: Use the context7 MCP server strategically to fetch documentation ONLY when needed to avoid context window overload.

#### Why This Is Critical
- As an LLM, I have a knowledge cutoff and may not be aware of newer library versions
- Libraries frequently update their APIs, deprecate features, and introduce new patterns
- Using outdated patterns leads to technical debt and potential security vulnerabilities
- The context7 MCP server provides real-time, accurate documentation

#### OPTIMIZED context7 Usage Strategy

**IMPORTANT: To prevent context window issues, follow these strict guidelines:**

1. **Use context7 ONLY when you need specific information**:
   - DO NOT preload documentation at the start of tasks
   - DO NOT fetch entire library docs unless absolutely necessary
   - Request only the specific topic/feature you're implementing
   - Use small token limits (1000-3000) for targeted queries

2. **When to use context7**:
   - When implementing a SPECIFIC feature (not general exploration)
   - When you encounter an error that might be version-related
   - When adding a NEW dependency (to check latest version and basic usage)
   - When the user explicitly asks about current library features

3. **How to use context7 efficiently**:
   ```
   # WRONG: Loading everything upfront
   - Don't: Load all FastAPI docs when starting any API work
   - Don't: Request 10000+ tokens of general documentation

   # RIGHT: Load exactly what you need, when you need it
   - Do: "I need to implement JWT auth, let me check FastAPI's current JWT patterns"
   - Do: Use specific topics like "jwt", "authentication", "dependencies"
   - Do: Use token limit of 2000-3000 for specific queries
   ```

4. **Efficient research workflow**:
   ```python
   # Step 1: Try to implement with existing knowledge
   # Step 2: If unsure about specific API/pattern:
   #   - Use context7 with specific topic and low token limit
   #   - Example: get docs for "pydantic field validators" with 2000 tokens
   # Step 3: Implement based on findings
   ```

5. **Common scenarios and token limits**:
   - **Checking latest version**: 500 tokens
   - **Specific feature/API**: 1000-2000 tokens
   - **Implementation pattern**: 2000-3000 tokens
   - **Complex integration**: 3000-5000 tokens (only if necessary)
   - **Never exceed 5000 tokens** unless explicitly justified

6. **Before using context7, ask yourself**:
   - Do I need this information RIGHT NOW for the current task?
   - Can I implement with my existing knowledge and verify later?
   - Am I being specific enough with my query?
   - Have I set an appropriate token limit?

### CRITICAL: Pre-Implementation Analysis Framework

**THIS IS MANDATORY FOR EVERY SINGLE LINE OF CODE YOU WRITE**

Before implementing ANYTHING (code, configuration, dependencies, or documentation), you MUST complete this analysis:

#### 1. Project Context Analysis
- **Read existing code** - Search for similar functionality/patterns in the codebase
- **Identify conventions** - How does THIS project handle:
  - Error handling and exceptions
  - Logging and debugging
  - Data validation
  - API responses
  - Database operations
  - Testing patterns
  - File organization
  - Naming conventions
  - Import organization
- **Check for existing utilities** - Never recreate what already exists
- **Understand the domain** - How does this fit into the business logic?

#### 2. Implementation Questions to Answer
Before writing ANY code, you MUST be able to answer:
- How does the existing codebase handle this type of functionality?
- What patterns are already established for this?
- Are there existing utilities or base classes I should use?
- What naming conventions does the project use for this?
- How are similar features tested in this project?
- What error handling patterns are used?
- How is logging implemented?

#### 3. When Patterns Are Unclear
If you cannot find clear patterns:
1. **STOP and analyze more** - Use grep/search to find similar cases
2. **Ask explicit questions** - "I noticed the project doesn't have established patterns for X. How would you like me to implement this?"
3. **Never assume** - Generic solutions are FORBIDDEN

#### 4. Examples of Project-Specific Analysis

**BAD (Generic)**:
```python
# Generic error handling
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

**GOOD (Project-Specific)**:
```python
# First, analyze how THIS project handles errors
# Search: grep -r "except\|raise\|error" --include="*.py"
# Found: Project uses custom exceptions in domain/*/exceptions.py
# Found: Project uses specific error response patterns
# Then implement following discovered patterns
```

### Pre-Implementation Checklist

**MANDATORY**: Before adding ANY dependency, tool, or configuration, you MUST:

1. **Check existing dependencies** - Read pyproject.toml to see what's already installed and their versions
2. **Verify tool configuration** - Only add hooks/configs for tools that are already set up in the project
3. **Check latest versions** - Use PyPI API or official repos to get the LATEST version of any library
4. **Read project context** - Review CLAUDE.md and existing configs to understand project-specific choices
5. **Validate compatibility** - Ensure new additions are compatible with existing tools and Python version
6. **Update ALL necessary configurations** - When adding dependencies, check if pre-commit hooks or other tools need updates

**Example verification commands**:
```bash
# Check latest version of a package
curl -s https://pypi.org/pypi/<package-name>/json | grep -o '"version":"[^"]*"' | head -1

# Check latest GitHub release
curl -s https://api.github.com/repos/<owner>/<repo>/releases/latest | grep '"tag_name"'

# Review current dependencies
cat pyproject.toml | grep -A 20 "dependencies"
```

### Implementation Workflow

**EVERY implementation MUST follow this workflow:**

1. **Research Library Documentation FIRST**
   - Use context7 MCP server to get current docs for any libraries you'll use
   - This MUST happen before writing any code
   - Example: Before using FastAPI, research current routing patterns
   - Example: Before using Pydantic, research current model validation

2. **Analyze Project Patterns**
   ```bash
   # Search for existing patterns
   uv run rg "pattern|keyword" --type py
   uv run rg "ClassName|function_name" --type py

   # Understand file organization
   ls -la src/domain/
   ls -la src/api/

   # Check for utilities
   find . -name "*util*" -o -name "*helper*" -o -name "*base*" | grep -v __pycache__
   ```

3. **Document Your Findings**
   - State what patterns you found
   - Explain which conventions you'll follow
   - If no patterns exist, ASK before proceeding

4. **Implement Following Project Patterns**
   - Use exact same error handling as found
   - Follow same logging approach
   - Match file organization
   - Use consistent naming

5. **Verify Consistency**
   - Your code should look like it belongs in THIS codebase
   - It should follow ALL discovered patterns
   - Generic solutions are NEVER acceptable

### Library Version Policy
- **ALWAYS use the absolutely latest version of any library** when adding dependencies
- Only use older versions if there are compatibility issues with other project dependencies
- This policy ensures we have the latest features, performance improvements, and security patches

### Special Case: Empty or Minimal Projects

When the project has little existing code:
1. **Reference the documented architecture** - Use the FastAPI structure documented below
2. **Ask for preferences** - "The project doesn't have established patterns for X yet. Would you like me to implement using [specific approach] or do you have a preference?"
3. **Start patterns thoughtfully** - Your first implementation sets the pattern for future code
4. **Document decisions** - Add comments explaining why you chose specific approaches

### Git Commit Policy
- **NEVER include AI tool references in commit messages**
- Do not add "Generated with Claude Code" or similar attributions
- Do not include "Co-Authored-By: Claude" or any AI authorship
- Follow the conventional commit format without any AI mentions

## FastAPI Project Structure

**Note**: This structure represents the target architecture. Currently, only the basic structure exists with configuration management implemented.

Follow domain-driven design with domain-centric organization and clear separation of cross-cutting concerns:

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py         # FastAPI app initialization
│   ├── middleware/     # API-specific middleware
│   │   ├── __init__.py
│   │   ├── request_context.py   # Correlation ID injection
│   │   ├── request_logging.py   # HTTP request/response logging
│   │   ├── security_headers.py  # Security headers middleware
│   │   └── error_handler.py     # Global exception handling
│   ├── schemas/        # API-specific schemas
│   │   ├── __init__.py
│   │   └── errors.py   # Error response models
│   └── v1/
│       ├── __init__.py
│       ├── endpoints/  # API endpoints by domain
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── users.py
│       │   └── [other_endpoints].py
│       └── dependencies.py  # API-wide dependencies
├── domain/             # Business domains with all related code
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── schemas.py      # Pydantic models (DTOs)
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── repository.py   # Data access layer
│   │   ├── service.py      # Business logic
│   │   ├── exceptions.py   # Domain-specific exceptions
│   │   └── constants.py    # Domain constants
│   ├── users/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   └── [other_domains]/
│       └── (same structure)
├── infrastructure/     # Technical infrastructure only
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py         # Base model and declarative base
│   │   ├── session.py      # Async session management
│   │   ├── repository.py   # Base repository pattern
│   │   └── dependencies.py # Database dependency injection
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis.py
│   └── external/           # Third-party integrations
│       ├── __init__.py
│       ├── email.py
│       └── storage.py
├── core/               # Application-wide shared code
│   ├── __init__.py
│   ├── config.py           # Settings management (Pydantic Settings)
│   ├── exceptions.py       # Base exceptions and error codes
│   ├── logging.py          # Logging setup and utilities
│   ├── context.py          # Request context and correlation IDs
│   ├── observability.py    # OpenTelemetry setup for GCP
│   ├── security.py         # Security utilities
│   └── utils.py           # Common utilities
└── cli/                # CLI commands
    ├── __init__.py
    └── commands.py

tests/                  # Mirror src structure
├── unit/
│   ├── api/
│   │   ├── middleware/
│   │   └── schemas/
│   ├── domain/
│   │   ├── auth/
│   │   └── users/
│   ├── infrastructure/
│   │   └── database/
│   └── core/
├── integration/
│   ├── api/
│   └── domain/
├── conftest.py        # Pytest fixtures
└── factories.py       # Test data factories

alembic/               # Database migrations
├── versions/
├── alembic.ini
├── env.py
└── script.py.mako

scripts/               # Development and deployment scripts
├── start.sh
├── test.sh
└── migrate.sh

config/                # Configuration files
├── .env.example
├── logging.yaml
└── gunicorn.conf.py
```

### Key Design Decisions:

1. **Clear Separation of Concerns**:
   - **API Layer**: HTTP-specific concerns (middleware, routing, request/response handling)
   - **Core Layer**: Shared cross-cutting concerns (exceptions, logging, context)
   - **Infrastructure Layer**: Technical implementations (database, cache, external services)
   - **Domain Layer**: Business logic and domain models

2. **Cross-Cutting Concerns Architecture**:
   - **Exceptions**: Base exceptions in `core/exceptions.py`, domain-specific in each domain
   - **Logging**: Centralized setup in `core/logging.py`, used throughout the application
   - **Context**: Request context and correlation IDs in `core/context.py`
   - **Observability**: OpenTelemetry configuration in `core/observability.py` for GCP integration

3. **Middleware Organization**:
   - API-specific middleware in `api/middleware/` (security headers, request logging)
   - Shared utilities in `core/` that can be used by both API and service layers

4. **Database Architecture**:
   - Async-first with SQLAlchemy 2.0 and asyncpg
   - Base repository pattern in `infrastructure/database/repository.py`
   - Domain repositories inherit from base repository
   - Alembic for migration management

5. **Testing Strategy**:
   - Unit tests mirror source structure
   - Integration tests for cross-component testing
   - Fixtures in `conftest.py` for test database and async support

This structure promotes domain cohesion while maintaining clean separation between business logic, technical infrastructure, and cross-cutting concerns.

## Concrete Example: Adding a New Feature

**Scenario**: Need to add user authentication

**WRONG Approach**:
```python
# Just start coding generic auth without checking project patterns
from fastapi import FastAPI, HTTPException
import jwt  # Adding random JWT library

@app.post("/login")
def login(username: str, password: str):
    # Generic implementation
    ...
```

**RIGHT Approach**:
1. **Research Current Library Docs**: "First, let me get up-to-date FastAPI documentation for authentication patterns"
   - Use context7 to research FastAPI authentication
   - Use context7 to research JWT libraries (python-jose, pyjwt)
   - Check current best practices for password hashing

2. **Analyze**: "Now let me check how this project handles authentication"
   - Check `src/domain/auth/` structure
   - Look for existing auth patterns
   - Search for security utilities

3. **Findings**: "I found that the project structure shows auth should go in `domain/auth/` with specific files for schemas, models, repository, and service. However, no implementation exists yet. Based on current FastAPI docs, the recommended approach is..."

4. **Ask**: "I see the project has a planned structure for authentication in `domain/auth/`. Should I implement following the documented domain-driven design pattern with:
   - Schemas in `domain/auth/schemas.py` using Pydantic v2 patterns
   - Business logic in `domain/auth/service.py`
   - Repository pattern in `domain/auth/repository.py`
   - JWT handling using python-jose (current version: X.X.X)
   Or would you prefer a different approach?"

5. **Implement**: Only after confirmation, following exact project structure and current library patterns

## Current Project Structure

The project has begun implementation with the following structure:

```
src/
├── api/
│   ├── __init__.py
│   └── main.py         # FastAPI app with /info endpoint
├── core/
│   ├── __init__.py
│   └── config.py       # Pydantic Settings configuration
└── domain/             # Empty, ready for domain implementations

tests/
├── unit/
│   ├── core/
│   │   ├── __init__.py
│   │   └── test_config.py  # Configuration tests
│   └── test_main.py        # Main entry point tests
└── integration/
    └── test_config_integration.py  # Configuration integration tests

main.py                 # Application entry point with uvicorn
.env.example            # Example environment variables
vulture_whitelist.py    # Whitelist for false positive dead code
```

## Exception Handling Patterns

### Base Exception Architecture

The project uses a centralized exception handling approach with:

1. **Base Exception Class**: `TributumError` in `src/core/exceptions.py`
   - All custom exceptions inherit from `TributumError`
   - Includes `error_code` and `message` attributes
   - Supports both string error codes and `ErrorCode` enum values

2. **Error Code Enum**: `ErrorCode` in `src/core/exceptions.py`
   - Standardized error codes using UPPER_SNAKE_CASE naming
   - Currently defined codes:
     - `INTERNAL_ERROR`: System-level unexpected errors
     - `VALIDATION_ERROR`: Input validation failures
     - `NOT_FOUND`: Resource not found errors
     - `UNAUTHORIZED`: Authentication/authorization failures

3. **Specialized Exception Classes**: Pre-built exceptions for common scenarios
   - `ValidationError`: Input validation failures (defaults to VALIDATION_ERROR)
   - `NotFoundError`: Missing resources (defaults to NOT_FOUND)
   - `UnauthorizedError`: Auth failures (defaults to UNAUTHORIZED)
   - `BusinessRuleError`: Business logic violations (defaults to INTERNAL_ERROR)

### Exception Usage Examples

```python
from src.core.exceptions import (
    TributumError, ErrorCode, ValidationError,
    NotFoundError, UnauthorizedError, BusinessRuleError
)

# Using base exception with ErrorCode enum
raise TributumError(ErrorCode.NOT_FOUND, "User with ID 123 not found")

# Using specialized exceptions (preferred for common cases)
raise ValidationError("Email must be a valid format")
raise NotFoundError("User with ID 123 not found")
raise UnauthorizedError("Invalid API key")
raise BusinessRuleError("Order cannot be processed with zero items")

# Specialized exceptions with custom error codes
raise ValidationError("Invalid format", "CUSTOM_VALIDATION_ERROR")

# Exception will format as: "[ERROR_CODE] message"
# Example: "[NOT_FOUND] User with ID 123 not found"
```

### Exception Design Patterns

1. **Message-First API**: Specialized exceptions take message as first parameter
   - More ergonomic: `ValidationError("Invalid email")`
   - Matches Python's built-in exception patterns

2. **Default Error Codes**: Each specialized exception has a sensible default
   - Reduces boilerplate while maintaining flexibility
   - Can still override with custom codes when needed

3. **When to Use Each Exception**:
   - `ValidationError`: User input doesn't meet format/type requirements
   - `NotFoundError`: Database queries return no results, missing files, etc.
   - `UnauthorizedError`: Failed authentication or insufficient permissions
   - `BusinessRuleError`: Valid input but violates business logic
   - `TributumError`: Base class for custom/unusual error scenarios

### Testing Patterns for Exceptions

When testing exceptions:
- Always test both the error code and message
- Use `pytest.raises` context manager
- Example:
  ```python
  with pytest.raises(TributumError) as exc_info:
      raise TributumError(ErrorCode.VALIDATION_ERROR, "Invalid input")

  assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR.value
  assert exc_info.value.message == "Invalid input"
  ```

### Naming Conventions

- **Exception Classes**: Use "Error" suffix (e.g., `TributumError`, `ValidationError`)
  - This follows Ruff's N818 linting rule
  - Do NOT use "Exception" suffix
- **Error Codes**: Use UPPER_SNAKE_CASE (e.g., `NOT_FOUND`, `VALIDATION_ERROR`)
- **Error Messages**: Use clear, user-friendly language without technical jargon

## API Error Response Pattern

### Error Response Model

The project uses a standardized `ErrorResponse` model in `src/api/schemas/errors.py` for all API errors:

```python
from src.api.schemas.errors import ErrorResponse

# Basic error response
error = ErrorResponse(
    error_code="VALIDATION_ERROR",
    message="Invalid email format"
)

# Error with additional details
error = ErrorResponse(
    error_code="VALIDATION_ERROR",
    message="Multiple validation errors",
    details={
        "email": "Invalid format",
        "password": "Too short"
    },
    correlation_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### Error Response Structure

All API errors return JSON with this structure:
```json
{
    "error_code": "NOT_FOUND",
    "message": "User with ID 123 not found",
    "details": null,  // Optional: Additional error context
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"  // Optional
}
```

### Pydantic Model Best Practices

1. **Field Documentation**: Use Pydantic's `Field` for descriptions and examples
   ```python
   error_code: str = Field(
       ...,
       description="Unique error code identifying the error type",
       examples=["VALIDATION_ERROR", "NOT_FOUND"]
   )
   ```

2. **Model Configuration**: Include response examples in `model_config`
   ```python
   model_config = {
       "json_schema_extra": {
           "examples": [...]
       }
   }
   ```

3. **Testing Pydantic Validation**: Use `model_validate` for type-safe testing
   ```python
   # Instead of: ErrorResponse(message="test")  # type error
   # Use: ErrorResponse.model_validate({"message": "test"})  # validation error
   ```

### Integration with Exception System

The `ErrorResponse` model is designed to work seamlessly with our exception system:
- `error_code` maps to `ErrorCode` enum values or custom codes
- `message` comes from the exception message
- `details` can include field-specific validation errors
- `correlation_id` will be injected by middleware (Phase 3)

## Recent Updates

### December 2024
- **Configuration Management**: Implemented Pydantic Settings v2 for centralized configuration
- **FastAPI Integration**: Basic FastAPI app with configuration dependency injection
- **Exception Infrastructure**:
  - Implemented `TributumError` base exception class with error codes
  - Added `ErrorCode` enum for standardized error identification
  - Created specialized exceptions: ValidationError, NotFoundError, UnauthorizedError, BusinessRuleError
  - Established exception naming convention (Error suffix, not Exception)
  - Implemented message-first API design for better ergonomics
  - Created `ErrorResponse` Pydantic model for standardized API error responses
- **Security Updates**: Updated safety from deprecated `check` to `scan` command
- **Pre-commit Optimizations**:
  - Reordered hooks to run ruff-format before other checks for efficiency
  - Added `pydantic-settings` to mypy dependencies
  - Configured pip-audit to ignore PYSEC-2022-42969 (py package vulnerability from interrogate)
  - Fixed all linting, formatting, and type checking issues
- **Testing**: Added comprehensive unit and integration tests for configuration and exceptions

## Known Issues

### Security Vulnerabilities
- **PYSEC-2022-42969**: The `py` package (v1.11.0) has a ReDoS vulnerability in SVN handling. This is a transitive dependency of `interrogate`. Since we don't use SVN features, this vulnerability is acknowledged and ignored in pip-audit.

### Tool Limitations
- **Safety CLI**: Requires authentication for `safety scan`. The check continues with `|| true` in automation.

## Notes

This file should be updated as the project develops to include:
- Domain implementations as they are created
- API endpoint documentation as they are added
- Database schema and migration patterns once database is integrated
- Authentication and authorization patterns once implemented
