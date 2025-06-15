# Tributum

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688.svg)](https://fastapi.tiangolo.com)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A modern Python backend API built with FastAPI, designed for financial and tax-related operations with centralized configuration management and comprehensive development tooling.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Overview

Tributum is a backend API system built with FastAPI, currently in its initial development phase. The project is designed to handle financial, tax, or payment-related operations (as suggested by the name "tributum" - Latin for "tribute" or "tax").

### Current Status

- [x] Development environment setup complete
- [x] Infrastructure as Code (Terraform) configured
- [x] Comprehensive code quality tooling integrated
- [x] Security scanning tools configured (Bandit, Safety, pip-audit, Semgrep)
- [x] FastAPI application scaffold implemented
- [x] Centralized configuration management with Pydantic Settings v2
- [x] Exception infrastructure with specialized error classes
- [x] Standardized API error response patterns
- [x] API endpoints: `/` (hello world) and `/info` (application information)
- [ ] Database integration pending
- [ ] Authentication system pending
- [ ] Business logic development not started

## Architecture

The project follows Domain-Driven Design (DDD) principles with a domain-centric architecture:

```
src/
├── api/                    # API layer (FastAPI endpoints)
│   ├── __init__.py
│   ├── main.py            # FastAPI app with / and /info endpoints
│   ├── middleware/        # API middleware (planned)
│   └── schemas/           # API request/response models
│       ├── __init__.py
│       └── errors.py      # ErrorResponse model
├── core/                  # Application-wide shared code
│   ├── __init__.py
│   ├── config.py          # Centralized configuration with Pydantic Settings v2
│   └── exceptions.py      # Base exceptions and ErrorCode enum
├── domain/                # Business domains (planned)
│   ├── auth/              # Authentication domain
│   ├── users/             # Users domain
│   └── [other_domains]/   # Additional business domains
└── infrastructure/        # Technical infrastructure (planned)
```

### Key Architectural Decisions

1. **Domain-Centric Organization**: Each domain contains all its related code (models, schemas, services, repositories)
2. **Clean Architecture**: Clear separation between business logic and technical infrastructure
3. **Repository Pattern**: For data access abstraction
4. **Service Layer**: For business logic encapsulation
5. **Structured Error Handling**: Specialized exception classes with standardized error codes
6. **Consistent API Responses**: All errors use the same response structure

## Tech Stack

### Backend
- **Language**: Python 3.13
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) 0.115.12
- **Configuration**: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 2.9.1
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/) 0.34.3
- **Package Manager**: [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

### Infrastructure
- **Cloud Provider**: Google Cloud Platform (GCP)
- **IaC**: Terraform >= 1.10.0
- **Container**: Docker (planned)

### Development Tools
- **Linting & Formatting**: [Ruff](https://github.com/astral-sh/ruff) 0.11.13
- **Type Checking**: [mypy](http://mypy-lang.org/) 1.16.0 (strict mode)
- **Git Hooks**: [pre-commit](https://pre-commit.com/) 4.2.0
- **Build Tool**: GNU Make
- **Version Control**: Git with conventional commits
- **Dead Code Detection**: [Vulture](https://github.com/jendrikseipp/vulture) 2.14
- **Docstring Coverage**: [Interrogate](https://interrogate.readthedocs.io/) 1.7.0

### Testing Tools
- **Test Framework**: [pytest](https://pytest.org/) 8.4.0
- **Coverage**: [pytest-cov](https://pytest-cov.readthedocs.io/) 6.2.1 (80% minimum)
- **Async Testing**: [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) 1.0.0
- **HTTP Testing**: [httpx](https://www.python-httpx.org/) 0.28.1
- **Parallel Testing**: [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) 3.6.1
- **Test Timeout**: [pytest-timeout](https://pypi.org/project/pytest-timeout/) 2.4.0
- **Rich Output**: [pytest-rich](https://github.com/nicoddemus/pytest-rich) 0.2.0

### Security Tools
- **Code Security**: [Bandit](https://github.com/PyCQA/bandit) 1.8.3
- **Dependency Scanning**: [Safety](https://pyup.io/safety/) 3.5.2
- **Vulnerability Audit**: [pip-audit](https://github.com/pypa/pip-audit) 2.9.0
- **Static Analysis**: [Semgrep](https://semgrep.dev/) 1.125.0

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Terraform >= 1.10.0 (for infrastructure)
- Google Cloud SDK (for GCP deployment)
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/tributum-back.git
   cd tributum-back
   ```

2. **Install uv (if not already installed)**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Set up pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

5. **Verify installation**
   ```bash
   uv run python main.py
   # FastAPI server will start on http://localhost:8000
   ```

## Configuration

The project uses Pydantic Settings v2 for centralized configuration management with type safety and validation.

### Environment Variables

Create a `.env` file in the project root based on `.env.example`:

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

### Configuration Usage

The configuration is accessible through dependency injection in FastAPI endpoints:

```python
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
```

### Infrastructure Configuration

1. **Initialize Terraform**
   ```bash
   cd terraform/
   terraform init
   ```

2. **Configure GCP credentials**
   - Place your service account key at `.keys/tributum-new-infrastructure-as-code-*.json`
   - Update `terraform/terraform.tfvars` based on `terraform.tfvars.example`

## Core Patterns

### Error Handling

#### Exceptions
```python
from src.core.exceptions import (
    ErrorCode, ValidationError, NotFoundError,
    UnauthorizedError, BusinessRuleError
)

# Use specialized exceptions (preferred)
raise ValidationError("Invalid email format")
raise NotFoundError("User with ID 123 not found")
raise UnauthorizedError("Invalid API key")
raise BusinessRuleError("Insufficient balance for transaction")

# Exception naming: "Error" suffix, not "Exception"
# Error codes: INTERNAL_ERROR, VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED
```

#### API Error Responses
```python
from src.api.schemas.errors import ErrorResponse

# Standardized error responses
ErrorResponse(
    error_code="VALIDATION_ERROR",
    message="Invalid input data",
    details={"email": "Invalid format"},  # Optional field-specific errors
    correlation_id="550e8400-e29b-41d4-a716-446655440000"  # Optional tracing ID
)
```

### Dependency Injection

The project uses FastAPI's dependency injection system:

```python
from typing import Annotated
from fastapi import Depends
from src.core.config import Settings, get_settings

@app.get("/endpoint")
def endpoint(settings: Annotated[Settings, Depends(get_settings)]):
    return {"app": settings.app_name, "version": settings.app_version}
```

## Usage

### Running the Application

The FastAPI application can be started with:

```bash
# Run the production server
make run
# Or directly:
uv run python main.py

# Run development server with auto-reload
make dev
# Or with custom settings:
DEBUG=true API_PORT=8080 uv run python main.py

# The API endpoints are:
# - GET  / - Hello world endpoint
# - GET  /info - Application information (name, version, environment)
# - GET  /docs - Interactive API documentation (if DOCS_URL is set)
# - GET  /redoc - Alternative API documentation (if REDOC_URL is set)
```

### Development Commands

```bash
# Linting
uv run ruff check .
uv run ruff check --fix .

# Formatting
uv run ruff format .
uv run ruff format --check .

# Type checking
uv run mypy .
uv run mypy --show-error-codes .

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Security checks
make security  # Run all security scans
make security-bandit  # Code security scan
make security-deps  # Dependency vulnerability scan

# Code quality checks
make dead-code  # Check for unused code
make docstring-coverage  # Check documentation coverage
```

### Using Make Commands

The project includes a Makefile for common tasks:

```bash
make help               # Show all available commands
make install            # Install dependencies and setup
make run                # Run the FastAPI server
make dev                # Run FastAPI with auto-reload
make lint               # Run linting
make format             # Format code
make type-check         # Run type checking
make test               # Run all tests
make test-coverage      # Run tests with coverage report
make security           # Run all security checks
make dead-code          # Check for dead code using vulture
make dead-code-report   # Generate detailed dead code report
make docstring-coverage # Check docstring coverage
make docstring-badge    # Generate docstring coverage badge
make all-checks         # Run all quality checks
```

## Development

### Code Style and Standards

This project enforces strict code quality standards:

1. **Type Safety**: All code must be fully type annotated
2. **Linting**: Comprehensive Ruff configuration with 20+ rule sets
3. **Formatting**: Consistent code style (88 char lines, double quotes)
4. **Pre-commit**: Automatic checks before every commit

### Pre-Implementation Requirements

Before writing ANY code, you MUST:

1. Analyze existing patterns in the codebase
2. Follow established conventions exactly
3. Never implement generic solutions
4. Ask for clarification when patterns are unclear

See [CLAUDE.md](CLAUDE.md) for detailed guidelines.

### Git Workflow

We use conventional commits:

```bash
feat: add user authentication
fix: resolve database connection issue
docs: update API documentation
chore: update dependencies
```

### Setting Up Development Environment

1. **Create a virtual environment (managed by uv)**
   ```bash
   uv venv
   ```

2. **Install development dependencies**
   ```bash
   uv sync --all-extras
   ```

3. **Configure your IDE**
   - Enable Python 3.13 interpreter
   - Configure Ruff for linting
   - Enable mypy for type checking

## Testing

The project uses pytest for testing with comprehensive coverage requirements and advanced testing features.

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_main.py        # Tests for main.py entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_main.py    # Tests for FastAPI app
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── test_errors.py  # Tests for error response models
│   └── core/
│       ├── __init__.py
│       ├── test_config.py      # Configuration tests
│       └── test_exceptions.py  # Exception classes tests
├── integration/            # Integration tests
│   ├── test_api.py        # Tests for API endpoints
│   └── test_config_integration.py  # Configuration integration tests
└── conftest.py            # Shared fixtures and configuration
```

### Test Features

- **Automatic async support**: Tests async functions without manual event loop handling
- **Parallel execution**: Run tests concurrently for faster feedback
- **Coverage enforcement**: 80% minimum coverage requirement
- **Rich output**: Beautiful test result display with pytest-rich
- **Test isolation**: Each test runs in isolation with proper fixtures
- **Timeout protection**: Tests fail if they run longer than 10 seconds

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run tests with coverage report
make test-coverage

# Run tests in parallel for speed
make test-fast

# Run tests with verbose output
make test-verbose

# Re-run only failed tests
make test-failed
```

### Coverage Requirements

- Minimum coverage: 80%
- Coverage reports are generated in `htmlcov/` directory
- Pre-commit hooks run tests automatically (without coverage for speed)

### Test Categories

- **Unit tests** (`@pytest.mark.unit`): Test individual components in isolation
- **Integration tests** (`@pytest.mark.integration`): Test API endpoints and integrations

## Deployment

### Infrastructure Setup

1. **Bootstrap Terraform state bucket** (one-time setup)
   ```bash
   cd terraform/bootstrap/
   terraform init
   terraform apply
   ```

2. **Deploy infrastructure**
   ```bash
   cd terraform/
   terraform plan
   terraform apply
   ```

### Environment-Specific Deployment

The project supports three environments:
- Development (`terraform/environments/dev/`)
- Staging (`terraform/environments/staging/`)
- Production (`terraform/environments/production/`)

Deploy to a specific environment:
```bash
cd terraform/environments/dev/
terraform apply
```

## Project Structure

```
tributum-back/
├── .claude/                    # AI assistant custom commands
│   └── commands/              # Slash commands for development
├── .keys/                     # GCP service account keys (git-ignored)
├── src/                       # Application source code
│   ├── api/                  # API layer
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── middleware/      # API middleware (planned)
│   │   └── schemas/         # API models
│   │       ├── __init__.py
│   │       └── errors.py    # Error response models
│   └── core/                # Core utilities
│       ├── __init__.py
│       ├── config.py        # Configuration module
│       └── exceptions.py    # Exception classes
├── tests/                     # Test files
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── conftest.py          # Test configuration
├── terraform/                 # Infrastructure as Code
│   ├── bootstrap/            # State bucket setup
│   ├── environments/         # Environment configs
│   └── modules/             # Reusable modules
├── .bandit                   # Bandit security configuration
├── .gitignore                # Git ignore patterns
├── .pre-commit-config.yaml   # Pre-commit hooks configuration
├── CLAUDE.md                 # AI assistant guidelines
├── main.py                   # Application entry point
├── Makefile                  # Build automation
├── pyproject.toml           # Project configuration
├── README.md                # This file
├── uv.lock                  # Locked dependencies
└── vulture_whitelist.py     # Whitelist for vulture false positives
```

## Contributing

1. **Follow the pre-implementation analysis framework** (see CLAUDE.md)
2. **Ensure all code is type-annotated**
3. **Run pre-commit hooks before committing**
4. **Use conventional commit messages**
5. **Keep documentation up-to-date**

### Development Process

1. Create a feature branch
2. **MANDATORY**: Re-read CLAUDE.md Development Guidelines before ANY implementation
3. Analyze existing patterns in the codebase
4. Implement changes following project patterns exactly
5. Add tests for new functionality (80% coverage minimum)
6. Run all quality checks: `make all-checks`
7. Update documentation
8. Submit a pull request

### Critical Development Rules

1. **Never bypass quality checks** - No `# type: ignore`, `# noqa`, etc.
2. **Project-specific patterns only** - Generic solutions are forbidden
3. **Pre-implementation analysis is mandatory** - Study existing code first
4. **Re-read guidelines frequently** - Every 10-15 minutes during development

## Roadmap

### Phase 1: Foundation (Complete)
- [x] Project setup
- [x] Development tooling
- [x] Infrastructure configuration
- [x] FastAPI application scaffold
- [x] Centralized configuration management
- [x] Basic API endpoints with documentation

### Phase 2: Core Features
- [ ] User authentication system
- [ ] Database integration
- [ ] Core business logic
- [ ] API endpoints

### Phase 3: Advanced Features
- [ ] Advanced financial calculations
- [ ] Reporting system
- [ ] Third-party integrations
- [ ] Performance optimization

### Phase 4: Production Readiness
- [ ] Comprehensive testing
- [ ] Monitoring and logging
- [ ] Security hardening
- [ ] Documentation completion

### Recent Updates

#### December 2024
- Implemented centralized configuration management with Pydantic Settings v2
- Added `/info` endpoint for application information
- Updated security scanning commands for latest tool versions
- Added comprehensive configuration tests
- Improved documentation with context7 MCP server usage guidelines
- Implemented exception infrastructure with specialized error classes
- Added standardized API error response model (ErrorResponse)
- Streamlined CLAUDE.md development guidelines
- Enhanced test coverage for error handling components

### Known Issues

- **PYSEC-2022-42969**: The `py` package (v1.11.0) has a ReDoS vulnerability in SVN handling. This is a transitive dependency of `interrogate`. Since we don't use SVN features, this vulnerability is acknowledged and ignored in pip-audit.
- **Safety CLI**: Requires authentication for `safety scan`. The check continues with `|| true` in automation.

## License

[License information to be added]

---

**Note**: This project is currently in active development. Features and documentation will be updated as development progresses.

<!-- README-METADATA
Last Updated: 2025-15-06
Last Commit: e5068e7
Update Count: 8
Generated By: /readme command
-->
