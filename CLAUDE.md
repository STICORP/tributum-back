# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is currently an empty project in its initial setup phase. The project name suggests it may be related to financial, tax, or payment systems.

## Project Status

- **Current State**: Python project initialized with uv, Terraform infrastructure setup complete
- **Technology Stack**:
  - Backend: Python 3.13
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
- Basic file checks (trailing whitespace, file endings, etc.)
- Ruff linting and formatting
- Mypy type checking

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

1. **Analyze First**
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

2. **Document Your Findings**
   - State what patterns you found
   - Explain which conventions you'll follow
   - If no patterns exist, ASK before proceeding

3. **Implement Following Project Patterns**
   - Use exact same error handling as found
   - Follow same logging approach
   - Match file organization
   - Use consistent naming

4. **Verify Consistency**
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

## FastAPI Project Structure (Future Reference)

**Note**: The following FastAPI project structure is documented here for future reference when we begin developing the application. This structure does not currently exist in the codebase but represents the preferred organization pattern for when development begins.

Follow domain-driven design with domain-centric organization:

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py         # FastAPI app initialization
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
│   │   ├── session.py      # Database connection/session management
│   │   ├── base.py         # Base model and repository classes
│   │   └── migrations/     # Alembic migrations
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis.py
│   └── external/           # Third-party integrations
│       ├── __init__.py
│       ├── email.py
│       └── storage.py
├── core/               # Application-wide shared code
│   ├── __init__.py
│   ├── config.py           # Settings management
│   ├── security.py         # Security utilities
│   ├── exceptions.py       # Base exceptions
│   └── utils.py           # Common utilities
└── cli/                # CLI commands
    ├── __init__.py
    └── commands.py

tests/                  # Mirror src structure
├── unit/
│   ├── domain/
│   │   ├── auth/
│   │   └── users/
│   └── core/
├── integration/
│   ├── api/
│   └── domain/
├── conftest.py        # Pytest fixtures
└── factories.py       # Test data factories

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

1. **Domain-Centric Organization**: Each domain contains all its related code including models, repositories, schemas, and business logic
2. **Cohesive Domains**: Everything needed to understand and work with a domain is in one place
3. **Infrastructure for Technical Concerns**: Infrastructure layer only contains technical utilities (DB sessions, cache, external services)
4. **Shared Base Classes**: Common base classes for models and repositories live in infrastructure/database
5. **Clear Boundaries**: Each domain is self-contained but can depend on core utilities

This structure promotes domain cohesion while maintaining clean separation between business logic and technical infrastructure.

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
1. **Analyze**: "Let me check how this project handles authentication"
   - Check `src/domain/auth/` structure
   - Look for existing auth patterns
   - Search for security utilities

2. **Findings**: "I found that the project structure shows auth should go in `domain/auth/` with specific files for schemas, models, repository, and service. However, no implementation exists yet."

3. **Ask**: "I see the project has a planned structure for authentication in `domain/auth/`. Should I implement following the documented domain-driven design pattern with:
   - Schemas in `domain/auth/schemas.py`
   - Business logic in `domain/auth/service.py`
   - Repository pattern in `domain/auth/repository.py`
   Or would you prefer a different approach?"

4. **Implement**: Only after confirmation, following exact project structure

## Notes

This file should be updated as the project develops to include:
- Build, test, and lint commands once a technology stack is chosen
- High-level architecture decisions as they are made
- Key development workflows specific to this project
