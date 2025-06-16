# Tributum

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688.svg)](https://fastapi.tiangolo.com)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, scalable financial/tax/payment backend API system built with FastAPI and deployed on Google Cloud Platform.

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
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)

## Overview

Tributum (Latin for "tribute" or "tax") is a financial backend system designed to handle tax calculations, payment processing, and financial operations. Built with modern Python technologies and cloud-native principles, it provides a robust foundation for financial applications.

### Key Features

- **Type-Safe Configuration**: Pydantic Settings v2 for robust configuration management
- **Structured Logging**: Production-ready logging with structlog and correlation IDs
- **Exception Handling**: Comprehensive error handling with severity levels and context
- **API Standards**: RESTful API with OpenAPI documentation
- **Cloud-Native**: Designed for Google Cloud Platform deployment
- **Development Excellence**: Strict code quality standards with comprehensive tooling
- **Domain-Driven Design**: Clean architecture following DDD principles

### Current Status

The project is in active development (v0.1.0) with core infrastructure implemented. Business logic implementation is planned after completing cross-cutting concerns.

### Recent Updates
- High-performance JSON serialization with orjson (2-10x faster)
- Request context middleware with correlation ID tracking
- Async context propagation using contextvars
- Enhanced logging with automatic correlation ID injection

## Architecture

Tributum follows Domain-Driven Design (DDD) principles with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│            (FastAPI, Middleware, Schemas)               │
├─────────────────────────────────────────────────────────┤
│                  Domain Layer                           │
│         (Business Logic, Domain Models)                 │
├─────────────────────────────────────────────────────────┤
│                   Core Layer                            │
│      (Shared Utilities, Config, Exceptions)             │
├─────────────────────────────────────────────────────────┤
│              Infrastructure Layer                       │
│        (Database, External Services, Cache)             │
└─────────────────────────────────────────────────────────┘
```

### Design Decisions

- **FastAPI**: Chosen for automatic API documentation, type safety, and performance
- **Pydantic V2**: Provides robust data validation and settings management
- **Structlog**: Structured logging for better observability and debugging
- **Domain-Driven Design**: Enables complex business logic organization
- **Google Cloud Platform**: Scalable, managed cloud infrastructure

## Tech Stack

### Core Technologies

- **Language**: Python 3.13
- **Framework**: FastAPI 0.115.12
- **ASGI Server**: Uvicorn 0.34.3
- **Configuration**: Pydantic Settings 2.9.1
- **Logging**: Structlog 25.4.0
- **JSON Serialization**: orjson 3.10.18 (high-performance)
- **Package Manager**: uv (fast Python package installer)

### Infrastructure

- **Cloud Provider**: Google Cloud Platform
- **Infrastructure as Code**: Terraform >= 1.10.0
- **Container**: Docker (planned)
- **Database**: PostgreSQL with SQLAlchemy 2.0 (planned)

### Development Tools

- **Linting/Formatting**: Ruff
- **Type Checking**: mypy (strict mode)
- **Testing**: pytest with coverage
- **Security**: Bandit, Safety, pip-audit, Semgrep
- **Code Quality**: Vulture, Interrogate, Pylint (variable shadowing)
- **Git Hooks**: pre-commit

## Prerequisites

- Python 3.13 or higher
- uv (Python package installer)
- Git
- Google Cloud SDK (for deployment)
- Terraform >= 1.10.0 (for infrastructure)
- Make (optional, for convenience commands)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tributum-back.git
cd tributum-back
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync
```

### 4. Set Up Pre-commit Hooks

```bash
uv run pre-commit install
```

### 5. Copy Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Tributum uses environment variables for configuration. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Tributum |
| `APP_VERSION` | Application version | 0.1.0 |
| `ENVIRONMENT` | Environment (development/staging/production) | development |
| `DEBUG` | Debug mode | true |
| `API_HOST` | API host | 127.0.0.1 |
| `API_PORT` | API port | 8000 |
| `LOG_CONFIG__LOG_LEVEL` | Logging level | INFO |
| `LOG_CONFIG__LOG_FORMAT` | Log format (console/json) | console |
| `LOG_CONFIG__RENDER_JSON_LOGS` | Force JSON logs | false |

### Logging Configuration

The application uses structured logging with environment-aware defaults:
- **Development**: Colored console output for readability
- **Production**: JSON format for log aggregation

See `.env.example` for all available configuration options.

## Usage

### Running the Application

```bash
# Using Make
make run

# Or directly with uvicorn
uv run uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Basic API Endpoints

```bash
# Health check
curl http://localhost:8000/

# Application info
curl http://localhost:8000/info
```

## Development

### Code Quality Standards

This project enforces strict code quality standards. **Never bypass quality checks**.

#### Running Quality Checks

```bash
# Format code
uv run ruff format .

# Lint and fix
uv run ruff check . --fix

# Type checking
uv run mypy .

# Run all pre-commit checks
uv run pre-commit run --all-files
```

#### Security Checks

```bash
# Security scanning
uv run bandit -r . -c pyproject.toml
uv run safety scan
uv run pip-audit --ignore-vuln PYSEC-2022-42969
uv run semgrep --config=auto .
```

#### Code Quality Analysis

```bash
# Dead code detection
uv run vulture .

# Docstring coverage (80% minimum)
uv run interrogate -v .
```

### Development Guidelines

1. **Read CLAUDE.md** before writing any code
2. **Write quality code from the start** - pre-commit hooks are a safety net, not a crutch
3. **Follow existing patterns** - generic solutions are forbidden
4. **Complete file reads** - no partial reads under 2000 lines
5. **Run all checks** before committing

### Adding New Features

1. Check existing patterns using the Grep tool (Note: `uv run rg` may timeout)
2. Identify conventions for error handling, naming, testing
3. Follow the established project structure
4. Write tests with >80% coverage
5. Update documentation

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/core/test_config.py

# Run tests in parallel
uv run pytest -n auto
```

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
│   ├── api/       # API layer tests
│   └── core/      # Core utilities tests
├── integration/    # Integration tests
└── conftest.py    # Shared test fixtures
```

### Coverage Requirements

- Minimum coverage: 80%
- Coverage reports: `htmlcov/index.html`

### Code Quality Metrics

Tributum maintains high code quality standards:
- **Type Coverage**: 100% (enforced by mypy strict mode)
- **Test Coverage**: Minimum 80% (enforced in CI)
- **Docstring Coverage**: Minimum 80% (Google style)
- **Security**: No high/critical vulnerabilities allowed
- **Code Style**: Enforced by Ruff with comprehensive rules
- **Performance**: JSON operations optimized with orjson (2-10x faster)

## Deployment

### Infrastructure Setup

1. **Configure GCP Project**
   ```bash
   export TF_VAR_project_id="your-gcp-project-id"
   ```

2. **Initialize Terraform**
   ```bash
   cd terraform/environments/dev
   terraform init
   ```

3. **Plan Infrastructure**
   ```bash
   terraform plan
   ```

4. **Apply Infrastructure**
   ```bash
   terraform apply
   ```

### Environment-Specific Deployment

Tributum supports three environments:
- **Development**: For active development and testing
- **Staging**: Pre-production environment
- **Production**: Live environment

Each environment has its own Terraform configuration in `terraform/environments/`.

## Project Structure

```
tributum-back/
├── src/                    # Source code
│   ├── api/               # API layer
│   │   ├── main.py       # FastAPI application with ORJSONResponse
│   │   ├── middleware/   # API middleware
│   │   │   └── request_context.py # Correlation ID tracking
│   │   ├── schemas/      # Pydantic models
│   │   │   └── errors.py # Error response models
│   │   └── utils/        # API utilities
│   │       └── responses.py # ORJSONResponse for high-performance
│   ├── core/             # Core utilities
│   │   ├── config.py     # Configuration management
│   │   ├── context.py    # Request context and correlation IDs
│   │   ├── error_context.py # Error context utilities
│   │   ├── exceptions.py # Exception classes
│   │   └── logging.py    # Structured logging with orjson
│   └── domain/           # Business domains (planned)
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Test configuration
├── terraform/            # Infrastructure as Code
│   ├── modules/         # Reusable Terraform modules
│   └── environments/    # Environment configurations
├── docs/                # Documentation
├── .claude/             # AI assistant commands
├── pyproject.toml      # Project configuration
├── Makefile           # Convenience commands
├── CLAUDE.md         # Development guidelines
└── plan.md          # Implementation roadmap
```

## API Documentation

Once the application is running, comprehensive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Current Endpoints

- `GET /`: Health check endpoint
- `GET /info`: Application information

Additional endpoints will be added as business logic is implemented.

## Contributing

### Commit Conventions

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Strategy

- `main` or `master`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `release/*`: Release preparation

### Code Review Process

1. Create feature branch from `develop`
2. Make changes following guidelines
3. Ensure all tests pass
4. Create pull request
5. Address review feedback
6. Merge after approval

## Troubleshooting

### Common Issues

**Issue**: Import errors when running the application
- **Solution**: Ensure virtual environment is activated and dependencies are installed

**Issue**: Pre-commit hooks failing
- **Solution**: Run `uv run ruff format .` and `uv run ruff check . --fix`

**Issue**: Type checking errors
- **Solution**: Ensure type hints are complete and correct

**Issue**: Test coverage below 80%
- **Solution**: Add tests for uncovered code paths

**Issue**: `uv run rg` command timing out
- **Solution**: Use the Grep tool in the development environment instead

### Getting Help

1. Check existing documentation in `docs/`
2. Review CLAUDE.md for development guidelines
3. Search existing issues on GitHub
4. Create a new issue with detailed information

## Roadmap

### Phase 1: Infrastructure (In Progress)
- [x] Basic FastAPI setup
- [x] Configuration management
- [x] Exception handling
- [x] Error response standardization
- [x] Structured logging with structlog
- [x] Correlation ID generation
- [x] Request context infrastructure
- [x] Request context middleware for correlation IDs
- [x] High-performance JSON serialization (orjson)
- [x] Async context propagation (contextvars)
- [ ] Additional API middleware (security, rate limiting)
- [ ] OpenTelemetry integration
- [ ] Database setup (PostgreSQL + SQLAlchemy)

### Phase 2: Core Features (Planned)
- [ ] Authentication system
- [ ] User management
- [ ] Tax calculation engine
- [ ] Payment processing
- [ ] Reporting system

### Phase 3: Advanced Features (Future)
- [ ] Multi-tenant support
- [ ] Advanced analytics
- [ ] Webhook system
- [ ] Batch processing
- [ ] API versioning

## License

This project is licensed under the MIT License.

---

<!-- README-METADATA
Last Updated: 2025-06-16
Last Commit: 5bc4211
Update Count: 3
-->
