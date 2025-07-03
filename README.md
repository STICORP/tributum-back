# Tributum 🚀

> High-performance financial/tax/payment system built for scale and reliability

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](./coverage)
[![Type Coverage](https://img.shields.io/badge/mypy-100%25-brightgreen.svg)](./pyproject.toml)

**Status**: Active Development | **Team**: Engineering Only | **Visibility**: Private

---

## 📚 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [🏗️ Architecture Deep Dive](#️-architecture-deep-dive)
- [⚙️ Internal Frameworks Explained](#️-internal-frameworks-explained)
- [⚡ Tech Stack](#-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [🔧 Development Workflow](#-development-workflow)
- [📁 Project Structure](#-project-structure)
- [🛡️ Security Architecture](#️-security-architecture)
- [🧪 Testing Philosophy](#-testing-philosophy)
- [📊 Monitoring & Observability](#-monitoring--observability)
- [🔧 Configuration Management](#-configuration-management)
- [🐳 Docker Development](#-docker-development)
- [🚧 Infrastructure as Code](#-infrastructure-as-code)
- [🎯 Developer Tools & Automation](#-developer-tools--automation)
- [📋 Command Reference](#-command-reference)
- [📝 Version Management](#-version-management)
- [🎯 Troubleshooting Guide](#-troubleshooting-guide)
- [📊 Current Implementation Status](#-current-implementation-status)

---

## 🎯 Project Overview

**Tributum** is a fiscal intelligence system designed to handle complex financial, tax, and payment operations with enterprise-grade reliability. Built with Clean Architecture principles and prepared for Domain-Driven Design (DDD) implementation.

### Architecture Philosophy

- **Clean Architecture**: Clear separation of concerns with dependency rule enforcement
- **Async-First**: Built on Python's async/await for maximum concurrency
- **Type-Safe**: 100% type coverage with MyPy and Pyright in strict mode
- **Observable**: Comprehensive logging and distributed tracing built-in
- **Secure by Default**: Multiple security layers and automated scanning

---

## 🏗️ Architecture Deep Dive

### System Design

```mermaid
graph TB
    subgraph "API Layer"
        A[FastAPI App] --> B[Middleware Stack]
        B --> C[Route Handlers]
    end

    subgraph "Core Layer"
        D[Exceptions] --> E[Logging]
        E --> F[Context Management]
        F --> G[Configuration]
    end

    subgraph "Infrastructure"
        H[Database] --> I[Repositories]
        I --> J[SQLAlchemy ORM]
    end

    C --> D
    C --> I
    I --> J
```

### Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant H as Handler
    participant R as Repository
    participant D as Database

    C->>M: HTTP Request
    M->>M: Add Security Headers
    M->>M: Generate Correlation ID
    M->>M: Start Request Logging
    M->>H: Process Request
    H->>R: Data Operation
    R->>D: SQL Query
    D-->>R: Result
    R-->>H: Domain Object
    H-->>M: HTTP Response
    M->>M: Log Request/Response
    M-->>C: Final Response
```

### Key Architectural Decisions

1. **Correlation IDs**: UUID4-based request tracking throughout the system
2. **Structured Logging**: JSON logs with orjson for performance
3. **Exception Hierarchy**: Severity-based error handling with fingerprinting
4. **Configuration**: Pydantic Settings v2 with nested configuration support
5. **Middleware Stack**: Pure ASGI middleware for maximum performance

---

## ⚙️ Internal Frameworks Explained

### Exception Framework

```python
# Severity-based exception hierarchy
TributumError (base)
├── ValidationError (400) - Input validation failures
├── UnauthorizedError (401) - Authentication failures
├── NotFoundError (404) - Resource not found
└── BusinessRuleError (422) - Domain rule violations

# Usage with context capture
raise ValidationError(
    "Invalid email format",
    context={"field": "email", "value": "[REDACTED]"},
    severity=Severity.MEDIUM
)
```

### Logging Framework

```python
# Structured logging with automatic context
logger = get_logger()

# Automatic correlation ID binding
with logger.contextualize(correlation_id=correlation_id):
    logger.info("Processing payment", amount=100.00, currency="USD")
    # Output: {"event": "Processing payment", "correlation_id": "...",
    #          "amount": 100.00, "currency": "USD", "timestamp": "..."}
```

**Formatters Available**:

- `console`: Human-readable with colors (development)
- `json`: Standard JSON format
- `gcp`: Google Cloud Logging format
- `aws`: AWS CloudWatch format

### Request Context Management

```python
# Correlation ID propagation via contextvars
correlation_id = RequestContext.get_correlation_id()
# Automatically included in logs, errors, and responses
```

### Repository Pattern

```python
# Type-safe generic repository
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one_by(email=email)
```

---

## ⚡ Tech Stack

### Core Technologies

- **Language**: Python 3.13+
- **Framework**: FastAPI 0.115+ with Pydantic 2.11+
- **Database**: PostgreSQL with async SQLAlchemy 2.0+
- **ORM**: SQLAlchemy with async support
- **Logging**: Loguru with structured logging
- **Monitoring**: OpenTelemetry with pluggable exporters

### Development Tools

- **Code Quality**: Ruff (all rules enabled), MyPy + Pyright (strict mode)
- **Security**: Bandit, pip-audit, Safety, Semgrep
- **Testing**: Pytest with 100% coverage requirement
- **Pre-commit**: Comprehensive hooks for quality assurance
- **Documentation**: Google-style docstrings with pydoclint

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 17+
- UV package manager
- Make

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/daniel-jorge/tributum-back.git
cd tributum-back

# Install dependencies and setup pre-commit
make install

# Copy environment variables
cp .env.example .env

# Run database migrations
make migrate-up

# Start the development server
make dev
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

---

## 🔧 Development Workflow

### Daily Development

```bash
# Start development server with hot-reload
make dev

# Run tests in parallel
make test-fast

# Apply all safe fixes
make all-fixes

# Run all quality checks before committing
make all-checks
```

### Code Quality Pipeline

```mermaid
graph LR
    A[Write Code] --> B[Pre-commit Hooks]
    B --> C{Pass?}
    C -->|No| D[Auto-fix or Manual Fix]
    D --> A
    C -->|Yes| E[Commit]
    E --> F[CI Pipeline]
```

### Pre-commit Hooks

The project enforces quality through automated pre-commit hooks:

1. **Auto-fixes**: Safe fixes applied automatically
2. **Type Checking**: MyPy and Pyright must pass
3. **Linting**: Ruff with all rules enabled
4. **Security**: Multiple security scanners
5. **Tests**: All tests must pass with 100% coverage

---

## 📁 Project Structure

```
tributum-back/
├── src/                    # Application source code
│   ├── api/               # HTTP layer (FastAPI)
│   │   ├── middleware/    # Custom middleware
│   │   ├── schemas/       # Pydantic models
│   │   └── utils/         # API utilities
│   ├── core/              # Business logic & utilities
│   │   ├── config.py      # Settings management
│   │   ├── exceptions.py  # Exception hierarchy
│   │   ├── logging.py     # Logging configuration
│   │   └── observability.py # Tracing setup
│   └── infrastructure/    # External dependencies
│       └── database/      # Database layer
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Shared fixtures
├── terraform/            # Infrastructure as Code
├── docker/               # Docker configuration
├── migrations/           # Alembic migrations
└── scripts/              # Development scripts
```

---

## 🛡️ Security Architecture

### Security Layers

1. **Input Validation**: Pydantic models with strict validation
2. **Sanitization**: Automatic PII removal in logs and errors
3. **Security Headers**: Comprehensive security headers via middleware
4. **Dependency Scanning**: pip-audit, Safety, and Semgrep
5. **Code Analysis**: Bandit for security issues

### Sensitive Data Handling

```python
# Automatically redacted patterns
SENSITIVE_PATTERNS = [
    "password", "token", "secret", "key",
    "authorization", "x-api-key", "cpf", "cnpj"
]
```

### Security Headers Applied

- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restrictive permissions

---

## 🧪 Testing Philosophy

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Component interaction tests
└── fixtures/       # Shared test fixtures
```

### Testing Standards

- **100% Coverage**: Required for all code
- **Parallel Execution**: Tests run with pytest-xdist
- **Isolation**: Each test runs in a transaction that's rolled back
- **Async Support**: Full async/await test support
- **Mocking**: pytest-mock only (unittest.mock forbidden)

### Test Execution

```bash
# Run all tests
make test

# Run tests in parallel (fast)
make test-fast

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Generate coverage report
make test-coverage
```

---

## 📊 Monitoring & Observability

### Structured Logging

All logs include:

- Correlation ID for request tracking
- Structured context fields
- Automatic PII sanitization
- Performance metrics

### Distributed Tracing

OpenTelemetry integration with:

- Automatic instrumentation for FastAPI and SQLAlchemy
- Pluggable exporters (console, GCP, AWS, OTLP)
- Correlation ID propagation to spans
- Custom span creation support

### Metrics Collected

- Request rate, error rate, duration (RED metrics)
- Database query performance
- Slow request detection
- System resource usage

---

## 🔧 Configuration Management

### Environment Variables

```bash
# Core Settings
APP_NAME=tributum
ENVIRONMENT=development  # development|staging|production
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://user:pass@localhost/tributum
DATABASE_CONFIG__POOL_SIZE=10
DATABASE_CONFIG__MAX_OVERFLOW=20

# Logging
LOG_CONFIG__LOG_LEVEL=INFO
LOG_CONFIG__LOG_FORMATTER_TYPE=console  # console|json|gcp|aws

# Observability
OBSERVABILITY_CONFIG__ENABLE_TRACING=true
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console  # console|gcp|aws|otlp
```

### Configuration Features

- **Nested Configuration**: Use `__` delimiter for nested values
- **Auto-detection**: Cloud environment detection for appropriate defaults
- **Validation**: All settings validated at startup
- **Type Safety**: Full type hints with Pydantic

---

## 🐳 Docker Development

### Development Environment

```bash
# Start development environment with hot-reload
make docker-up-dev

# Run tests in Docker
make docker-test

# Access container shell
make docker-shell

# View logs
make docker-logs
```

### Docker Architecture

- **Multi-stage builds**: Optimized production images
- **Non-root user**: Security best practice
- **Development mode**: Hot-reload with volume mounts
- **Cloud Run ready**: Respects PORT environment variable

---

## 🚧 Infrastructure as Code

### Terraform Structure

```
terraform/
├── bootstrap/          # Initial setup
├── environments/       # Environment-specific configs
│   ├── dev/
│   ├── staging/
│   └── production/
├── main.tf            # Main configuration
├── variables.tf       # Variable definitions
└── outputs.tf         # Output definitions
```

The project uses Terraform for infrastructure management with support for multiple environments.

---

## 🎯 Developer Tools & Automation

### Claude Commands

The project includes specialized Claude AI commands in `.claude/commands/`:

- **Git & Version Control**: Commit creation, release management
- **Code Quality**: Implementation verification, dependency validation
- **Testing**: Missing test detection, coverage validation
- **Project Management**: Task breakdown, project analysis

### Automation Scripts

- `check-mock-imports.py`: Enforces pytest-mock usage
- `check-test-markers.py`: Validates test markers
- Pre-commit hooks for comprehensive quality checks

---

## 📋 Command Reference

### Essential Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies and pre-commit hooks |
| `make dev` | Start development server with hot-reload |
| `make run` | Run the FastAPI application |
| `make test-fast` | Run tests in parallel |
| `make all-checks` | Run all quality checks before committing |
| `make all-fixes` | Apply all safe auto-fixes |
| `make clean` | Clean up temporary files |

### Testing Commands

| Command | Description |
|---------|-------------|
| `make test` | Run all tests with coverage |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-coverage` | Generate HTML coverage report |
| `make test-failed` | Re-run only failed tests |
| `make test-verbose` | Run tests with verbose output |
| `make test-random` | Run tests with random ordering |
| `make test-no-random` | Run tests without randomization (debugging) |
| `make test-seed SEED=12345` | Run tests with specific seed |
| `make test-ci` | Run tests for CI (stop on first failure) |

### Code Quality

| Command | Description |
|---------|-------------|
| `make format` | Format code with Ruff |
| `make format-check` | Check code formatting without changes |
| `make lint` | Run linting checks |
| `make lint-fix` | Fix linting issues automatically |
| `make type-check` | Run MyPy type checking |
| `make pyright` | Run Pyright/Pylance type checking |
| `make complexity-check` | Check code complexity (McCabe) |
| `make dead-code` | Check for dead code using vulture |
| `make docstring-check` | Check docstring presence and quality |
| `make pylint-check` | Run pylint for code quality |
| `make shellcheck` | Check shell scripts |

### Security

| Command | Description |
|---------|-------------|
| `make security` | Run all security checks |
| `make security-bandit` | Run Bandit security scan |
| `make security-pip-audit` | Run pip-audit vulnerability scan |
| `make security-safety` | Run safety vulnerability scan |
| `make security-semgrep` | Run semgrep static analysis |
| `make security-deps` | Check dependencies for vulnerabilities |

### Database

| Command | Description |
|---------|-------------|
| `make migrate-create MSG="desc"` | Create new migration |
| `make migrate-up` | Apply pending migrations |
| `make migrate-down` | Rollback last migration |
| `make migrate-history` | Show migration history |
| `make migrate-current` | Show current migration revision |
| `make migrate-check` | Check for pending model changes |
| `make migrate-init` | Initialize database with all migrations |
| `make migrate-reset` | Reset database (DESTRUCTIVE!) |

### Docker Commands

| Command | Description |
|---------|-------------|
| `make docker-up-dev` | Start development environment |
| `make docker-up` | Start production environment |
| `make docker-down` | Stop all services |
| `make docker-build` | Build all Docker images |
| `make docker-test` | Run tests in Docker |
| `make docker-migrate` | Run migrations in Docker |
| `make docker-shell` | Shell into API container |
| `make docker-psql` | Connect to PostgreSQL |
| `make docker-logs` | View container logs |
| `make docker-clean` | Clean all Docker resources |

### Pre-commit & Validation

| Command | Description |
|---------|-------------|
| `make pre-commit` | Run all pre-commit hooks |
| `make mock-check` | Check for forbidden unittest.mock imports |
| `make markers-check` | Verify pytest markers in test files |

---

## 📝 Version Management

The project uses `bump-my-version` for semantic versioning:

```bash
# Current version
cat VERSION  # Shows 0.3.0

# Version bumping is handled through Claude commands
# Use the /create-release Claude command for version management
```

---

## 🎯 Troubleshooting Guide

### Common Issues

#### Import Errors

```bash
# Ensure Python 3.13 is active
python --version

# Reinstall dependencies
make install
```

#### Type Errors

```bash
# Clear MyPy cache
rm -rf .mypy_cache

# Reinstall type stubs
make install
```

#### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps

# Verify connection string
echo $DATABASE_CONFIG__DATABASE_URL

# Reset database
make migrate-reset
```

#### Pre-commit Hook Failures

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Run specific hook
pre-commit run mypy --all-files
```

---

## 📊 Current Implementation Status

### ✅ Implemented Features

- **FastAPI Application**: Core API with health and info endpoints
- **Exception Framework**: Comprehensive error handling with severity levels
- **Structured Logging**: JSON logging with multiple formatters
- **Request Context**: Correlation ID tracking across requests
- **Configuration Management**: Pydantic Settings with validation
- **Database Layer**: Async SQLAlchemy with repository pattern
- **Middleware Stack**: Security, logging, and context middleware
- **Testing Infrastructure**: 100% coverage with parallel execution
- **Development Tooling**: Comprehensive Make commands and pre-commit hooks
- **Docker Support**: Development and production configurations
- **CI/CD**: GitHub Actions for quality checks
- **Infrastructure as Code**: Terraform configuration

### 🏗️ Architecture Components

- **API Layer**: FastAPI with middleware stack and error handling
- **Core Layer**: Logging, exceptions, configuration, and observability
- **Infrastructure Layer**: Database with repository pattern
- **Domain Layer**: Structure prepared for DDD implementation

---

<!-- README-METADATA
Last Updated: 2025-07-03T13:32:48Z
Last Commit: 00f6714
Schema Version: 2.0
Sections: {
  "overview": {"hash": "a1b2c3", "manual": false},
  "architecture": {"hash": "d4e5f6", "manual": false},
  "tech-stack": {"hash": "g7h8i9", "manual": false},
  "quick-start": {"hash": "j1k2l3", "manual": false},
  "development": {"hash": "m4n5o6", "manual": false},
  "structure": {"hash": "p7q8r9", "manual": false},
  "security": {"hash": "s1t2u3", "manual": false},
  "testing": {"hash": "v4w5x6", "manual": false},
  "monitoring": {"hash": "y7z8a9", "manual": false},
  "configuration": {"hash": "b1c2d3", "manual": false},
  "docker": {"hash": "e4f5g6", "manual": false},
  "infrastructure": {"hash": "h7i8j9", "manual": false},
  "tools": {"hash": "k1l2m3", "manual": false},
  "commands": {"hash": "n4o5p6", "manual": false},
  "version": {"hash": "q7r8s9", "manual": false},
  "troubleshooting": {"hash": "t1u2v3", "manual": false},
  "status": {"hash": "w4x5y6", "manual": false}
}
-->
