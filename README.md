# Tributum 🚀

> High-performance financial/tax/payment system built for scale and reliability

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](./htmlcov/index.html)
[![Type Coverage](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](./pyproject.toml)

**Status**: Active Development | **Team**: Engineering Only | **Visibility**: Private

## 📚 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [⚙️ Tech Stack](#️-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture Deep Dive](#️-architecture-deep-dive)
- [🔧 Internal Frameworks Explained](#-internal-frameworks-explained)
- [📊 Observability & Monitoring](#-observability--monitoring)
- [🛡️ Security Architecture](#️-security-architecture)
- [🧪 Testing Philosophy](#-testing-philosophy)
- [💻 Development Workflow](#-development-workflow)
- [🎨 Developer Tools & Automation](#-developer-tools--automation)
- [🔄 CI/CD Pipeline](#-cicd-pipeline)
- [📋 Command Reference](#-command-reference)
- [📦 Version Management & Release Workflow](#-version-management--release-workflow)
- [🏢 Infrastructure](#-infrastructure)
- [🐳 Docker Infrastructure](#-docker-infrastructure)
- [💾 Database Configuration](#-database-configuration)
- [⚙️ Configuration Management](#️-configuration-management)
- [📁 Project Structure](#-project-structure)
- [🔍 Troubleshooting Guide](#-troubleshooting-guide)
- [🌐 API Endpoints](#-api-endpoints)
- [✅ Current Implementation Status](#-current-implementation-status)

## 🎯 Project Overview

**Purpose**: High-performance financial/tax/payment system designed for enterprise-scale operations with a focus on reliability, observability, and security.

**Architecture Philosophy**:

- Domain-Driven Design (DDD) for clear business logic separation
- Clean Architecture principles for testability and maintainability
- Event-driven patterns for scalability
- Infrastructure as Code with Terraform

**Core Principles**:

- **Type Safety**: 100% strict type checking with mypy and Pyright
- **Security First**: Multi-layered security scanning and input validation
- **Observable**: Structured logging with correlation IDs and distributed tracing
- **Performance**: ORJSONResponse for 3x faster JSON serialization
- **Quality**: Comprehensive testing with 100% code coverage achieved

## ⚙️ Tech Stack

### Core Framework

- **Python 3.13**: Latest Python with performance improvements
- **FastAPI 0.115+**: Modern async web framework
- **Pydantic v2**: Data validation with 50% performance boost
- **Structlog**: Structured logging with automatic context
- **ORJSON**: High-performance JSON serialization

### Database Stack

- **SQLAlchemy 2.0+**: Modern ORM with async support
- **asyncpg**: High-performance PostgreSQL async driver
- **Alembic**: Database migration management
- **PostgreSQL**: Primary database with connection pooling

### Observability Stack

- **OpenTelemetry**: Vendor-neutral instrumentation framework
- **OpenTelemetry FastAPI**: Automatic HTTP request tracing
- **OpenTelemetry SQLAlchemy**: Database query tracing
- **GCP Cloud Trace**: Distributed trace storage and analysis
- **Correlation IDs**: Request tracking across all layers

### Development Tools

- **UV**: Fast Python package manager (10x faster than pip)
- **Ruff**: Lightning-fast Python linter and formatter with ALL rules enabled by default
- **MyPy**: Static type checker with strict mode
- **Pyright**: Microsoft's type checker for enhanced IDE support
- **Pre-commit**: Git hooks for code quality
- **Pytest**: Testing framework with async support
- **Pytest-mock**: Improved mocking for cleaner test code
- **Pytest-env**: Centralized test environment configuration
- **Pytest-randomly**: Randomized test execution to detect inter-test dependencies
- **Pytest-check**: Soft assertions for comprehensive test failure reporting
- **Pytest-xdist**: Parallel test execution for faster CI/CD
- **Docker**: Containerization for development and production

### Security Tools

- **Bandit**: AST-based security scanner
- **Safety**: Dependency vulnerability scanner
- **Pip-audit**: Package audit tool
- **Semgrep**: Static analysis with custom rules

### Infrastructure

- **Terraform**: Infrastructure as Code
- **Google Cloud Platform**: Cloud provider (Cloud Run support)
- **GitHub Actions**: CI/CD pipeline
- **Docker**: Development and production containers
- **Docker Compose**: Multi-container orchestration

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/daniel-jorge/tributum-back
cd tributum-back

# One-command setup (creates venv, installs deps, configures hooks)
make install

# Run with auto-reload
make dev

# Run all quality checks
make all-checks
```

### Docker Development

```bash
# Start development environment with hot-reload
make docker-up-dev

# View logs
make docker-logs

# Access PostgreSQL
make docker-psql

# Run database migrations
make docker-migrate

# Stop containers
make docker-down
```

### Essential Commands

```bash
# Development
make dev              # Run with auto-reload
make test            # Run all tests
make test-coverage   # Generate coverage report

# Code Quality
make format          # Format code
make lint           # Run linting
make type-check     # Type checking
make pyright        # Pyright type checking
make all-checks     # Run all checks

# Security
make security       # Run all security scans
make security-deps  # Check dependencies only

# Docker
make docker-up-dev  # Development with hot-reload
make docker-test    # Run tests in Docker
make docker-clean   # Remove containers and volumes
```

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
        G --> H[Observability]
    end

    subgraph "Domain Layer"
        I[Business Logic] --> J[Domain Models]
        J --> K[Domain Services]
    end

    subgraph "Infrastructure Layer"
        L[Database Models] --> M[Repositories]
        M --> N[Session Management]
        N --> O[Connection Pool]
    end

    subgraph "External Services"
        P[PostgreSQL] --> Q[Redis Cache]
        Q --> R[GCP Cloud Trace]
    end

    C --> I
    I --> M
    M --> P
    H --> R
```

### Middleware Stack

The application uses a carefully ordered middleware stack for optimal request processing:

```mermaid
graph TB
    subgraph "Request Flow"
        A[HTTP Request] --> B[SecurityHeadersMiddleware]
        B --> C[RequestContextMiddleware]
        C --> D[RequestLoggingMiddleware]
        D --> E[OpenTelemetry Instrumentation]
        E --> F[Route Handler]
    end

    subgraph "Response Flow"
        F --> G[RequestLoggingMiddleware]
        G --> H[RequestContextMiddleware]
        H --> I[SecurityHeadersMiddleware]
        I --> J[HTTP Response]
    end
```

#### Middleware Components

1. **SecurityHeadersMiddleware** (Outermost)
   - Adds security headers to all responses
   - HSTS, X-Content-Type-Options, X-Frame-Options
   - CSP headers for XSS protection
   - Applied to both successful and error responses

2. **RequestContextMiddleware**
   - Creates UUID4 correlation IDs for request tracking
   - Stores context in contextvars for async safety
   - Adds X-Correlation-ID to response headers
   - Propagates context to logs and traces

3. **RequestLoggingMiddleware**
   - Logs request/response with correlation IDs
   - Captures request body (with size limits)
   - Records response time and status
   - Integrates with structured logging

4. **OpenTelemetry Instrumentation**
   - Automatic span creation for requests
   - Trace context propagation
   - Error recording in spans
   - Integration with Cloud Trace

The middleware are registered as pure ASGI middleware (not BaseHTTPMiddleware) for better performance and proper async handling.

### Request Flow with Tracing

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant T as OpenTelemetry
    participant H as Handler
    participant S as Service
    participant R as Repository
    participant D as Database
    participant CT as Cloud Trace

    C->>M: HTTP Request
    M->>M: Add Security Headers
    M->>M: Add Correlation ID
    M->>T: Start Span
    T->>M: Span Context
    M->>M: Start Request Logging
    M->>H: Process Request
    H->>S: Business Logic
    S->>R: Data Operation
    R->>D: SQL Query
    D-->>R: Result
    R-->>S: Domain Model
    S-->>H: Response
    H-->>M: HTTP Response
    M->>M: Log Request/Response
    M->>T: End Span
    T->>CT: Export Trace
    M-->>C: Final Response
```

### Key Architectural Decisions (ADRs)

1. **Correlation IDs**: UUID4-based request tracking for distributed tracing
2. **Structured Logging**: JSON logs with orjson for high-performance parsing (structlog configured to avoid test warnings)
3. **Exception Hierarchy**: Severity-based error handling with automatic context capture
4. **Configuration**: Pydantic Settings v2 with nested validation
5. **Middleware Stack**: Pure ASGI implementation for performance
6. **Response Serialization**: ORJSONResponse default for 3x faster JSON encoding
7. **Distributed Tracing**: OpenTelemetry with configurable sampling and GCP export
8. **Database Architecture**: Async PostgreSQL with connection pooling and pre-ping health checks
9. **Repository Pattern**: Generic base repository for consistent data access patterns
10. **Database IDs**: Sequential BigInteger IDs for performance and PostgreSQL optimization
11. **Database Lifecycle**: Managed in FastAPI lifespan with proper error handling
12. **Cloud Run Compatibility**: Respects PORT environment variable for container deployment
13. **Constants Architecture**: Layer-specific constants modules following clean architecture principles

## 🔧 Internal Frameworks Explained

### Exception Framework

```python
# Severity-based exception hierarchy
TributumError (base)
├── ValidationError (400) - Input validation failures
├── UnauthorizedError (401) - Auth failures
├── NotFoundError (404) - Resource not found
└── BusinessRuleError (422) - Domain rule violations

# Usage with automatic context capture
raise ValidationError(
    "Invalid email format",
    context={"field": "email", "value": "bad-email"},
    severity=Severity.MEDIUM
)
```

**Features**:

- Automatic stack trace capture
- Severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Error fingerprinting for deduplication
- Context sanitization for sensitive data
- Automatic span enrichment in traces

### Logging Framework

```python
# Structured logging with automatic context
logger = get_logger()

# Correlation ID automatically bound
with log_context(user_id=123, action="payment"):
    logger.info("Processing payment", amount=100.00)
    # Output: {"event": "Processing payment", "correlation_id": "...",
    #          "user_id": 123, "action": "payment", "amount": 100.00}
```

**Features**:

- Automatic correlation ID injection
- Context preservation across async boundaries
- Sensitive field redaction
- Console (dev) / JSON (prod/staging) formatters
- Integration with OpenTelemetry spans
- Configurable exc_info formatting to avoid test warnings

### Enhanced Logging Configuration

The logging system now supports advanced configuration options:

```python
class LogConfig:
    # Path exclusion for high-traffic endpoints
    excluded_paths: list[str] = ["/health", "/metrics"]

    # Sensitive field redaction
    sensitive_fields: list[str] = ["password", "token", "secret", "api_key"]

    # SQL query logging
    enable_sql_logging: bool = False
    slow_query_threshold_ms: int = 100

    # Performance and error context processors
    enable_performance_processor: bool = False
    enable_environment_processor: bool = True
    enable_error_context_processor: bool = True

    # Request/Response body logging
    log_request_body: bool = False
    log_response_body: bool = False
    max_body_log_size: int = 10240
```

### Request Context Management

```python
# Correlation ID propagation via contextvars
correlation_id = RequestContext.get_correlation_id()
# Automatically included in logs, errors, responses, and traces
```

**Features**:

- Thread-safe context storage
- Automatic propagation in async code
- X-Correlation-ID header support
- UUID4 generation with validation
- Span attribute enrichment
- Enhanced context binding and unbinding for complex scenarios

### Database Infrastructure

```python
# Base model with common fields
class BaseModel(Base):
    """Provides id, created_at, and updated_at for all models."""
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

# Generic repository pattern with extended CRUD
class BaseRepository[T: BaseModel]:
    """Extended CRUD operations for any model."""

    # Basic operations
    async def get_by_id(self, entity_id: int) -> T | None
    async def get_all(self) -> list[T]
    async def create(self, **kwargs) -> T

    # Extended operations
    async def update(self, entity: T, **kwargs) -> T
    async def delete(self, entity: T) -> None
    async def count(self) -> int
    async def exists(self, **filters) -> bool

    # Dynamic filtering
    async def filter_by(self, **filters) -> list[T]
    async def find_one_by(self, **filters) -> T | None

# Dependency injection
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session_maker() as session:
        yield session
```

**Features**:

- Async session management with connection pooling
- Generic repository pattern for consistent data access
- Automatic timestamps on all models
- Database dependency injection for FastAPI
- Transaction management with context managers
- Optimized for PostgreSQL with sequential IDs
- Extended CRUD operations with filtering
- Structured logging for all database operations

### Database Lifecycle Management

The application manages database connections through FastAPI's lifespan context:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await test_database_connection()  # Validates database is accessible

    # OpenTelemetry setup
    setup_opentelemetry(app)

    yield  # Application runs

    # Shutdown
    await dispose_database_engine()  # Closes all connections
```

### Observability Framework

```python
# Tracing with OpenTelemetry
from src.core.observability import get_tracer, record_tributum_error_in_span

tracer = get_tracer(__name__)

with tracer.start_as_current_span("payment_processing") as span:
    span.set_attribute("payment.amount", 100.00)
    span.set_attribute("payment.currency", "USD")

    try:
        # Business logic
        process_payment()
    except TributumError as e:
        # Automatic error context recording
        record_tributum_error_in_span(span, e)
        raise
```

**Features**:

- Automatic span creation for HTTP requests
- Database query tracing with SQLAlchemy instrumentation
- Correlation ID propagation to spans
- Error severity mapping to span status
- Configurable sampling rates
- GCP Cloud Trace integration

### Constants Architecture

The project now uses layer-specific constants modules:

```python
# API Layer (src/api/constants.py)
- HTTP status codes
- API configuration defaults
- Request handling limits
- Content types
- Security headers

# Core Layer (src/core/constants.py)
- Logging configuration
- Time units
- Security patterns for redaction

# Infrastructure Layer (src/infrastructure/constants.py)
- Database-specific settings
- Connection pool configuration
```

This separation ensures each layer only contains constants relevant to its responsibilities, preventing cross-layer dependencies.

## 📊 Observability & Monitoring

### Distributed Tracing

The application implements comprehensive distributed tracing using OpenTelemetry:

#### Automatic Instrumentation

- Every HTTP request automatically creates a span
- Database queries traced with SQLAlchemy instrumentation
- Correlation IDs are propagated to all spans
- Request metadata (path, method, status) captured
- Response times measured automatically

#### Manual Instrumentation

```python
# Create custom spans for business operations
tracer = get_tracer(__name__)

with tracer.start_as_current_span("calculate_tax") as span:
    span.set_attribute("tax.type", "income")
    span.set_attribute("tax.year", 2025)
    # Your business logic here
```

#### Error Tracking

- TributumError exceptions automatically enrich spans
- Severity levels mapped to span status codes
- Error context preserved in span attributes
- Stack traces captured for debugging

### GCP Cloud Trace Integration

When enabled, traces are exported to GCP Cloud Trace for:

- Distributed trace visualization
- Latency analysis
- Service dependency mapping
- Performance bottleneck identification

### Configuration

```bash
# Enable tracing
OBSERVABILITY_CONFIG__ENABLE_TRACING=true

# Configure GCP export
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id

# Set sampling rate (0.0 to 1.0)
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1  # 10% sampling

# Service identification
OBSERVABILITY_CONFIG__SERVICE_NAME=tributum
```

### Metrics Collected

- Request rate, error rate, duration (RED metrics)
- Database query performance metrics
- Connection pool statistics
- Business metrics (when instrumented)
- System metrics (CPU, memory, connections)
- Trace sampling statistics

### Log Aggregation

```json
{
  "timestamp": "2025-06-20T10:30:00Z",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "32e1a2b3c4d5e6f7g8h9i0j1k2l3m4n5",
  "span_id": "a1b2c3d4e5f6g7h8",
  "event": "payment.processed",
  "duration_ms": 45,
  "user_id": "user_123",
  "amount": 100.00,
  "currency": "USD"
}
```

## 🛡️ Security Architecture

### Security Layers

1. **Input Validation**: Pydantic models with strict mode enabled
2. **Sanitization**: Automatic PII removal in logs and error responses
3. **Security Headers**: HSTS, X-Content-Type-Options, X-Frame-Options
4. **Dependency Scanning**: Safety, pip-audit, and automated updates
5. **Static Analysis**: Bandit and Semgrep with custom rules

### Sensitive Data Handling

```python
SENSITIVE_PATTERNS = [
    "password", "token", "secret", "key",
    "authorization", "x-api-key", "ssn", "cpf",
    "credit_card", "cvv", "pin", "cookie"
]
# Automatically redacted in logs and error responses
```

### Security Scanning Pipeline

```bash
make security              # Run all security checks
├── bandit                # AST-based code analysis
├── safety                # Known vulnerabilities
├── pip-audit            # Package audit
└── semgrep              # Static analysis
```

## 🧪 Testing Philosophy

### Test Structure

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Component interaction tests
│   ├── api/       # API endpoint integration tests
│   │   └── error_handling/  # Comprehensive error handling tests
│   ├── test_fixture_isolation.py  # Database fixture isolation tests
│   └── test_full_stack.py         # End-to-end stack tests
├── fixtures/       # Environment-specific test fixtures
│   ├── test_database_fixtures.py  # Database test utilities
│   └── test_docker_fixtures.py    # Docker container management
├── conftest.py     # Shared fixtures and auto-clearing cache
└── coverage/       # Coverage reports (100% achieved)
```

### Testing Standards

- **Coverage Achievement**: 100% code coverage across entire codebase
- **Test Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
- **Async Testing**: Full async/await support with pytest-asyncio
- **Parallel Execution**: pytest-xdist for faster test runs with proper isolation
- **Rich Output**: pytest-rich for better test visualization (compatible with xdist)
- **Mocking**: pytest-mock for cleaner, more maintainable test code
- **Environment Management**: pytest-env for consistent test configuration
- **Test Randomization**: pytest-randomly for detecting test interdependencies
- **Soft Assertions**: pytest-check for comprehensive failure visibility

### Advanced Testing Features

#### Parallel Test Execution

The project now supports fully parallel test execution with proper database isolation:

```bash
# Run tests in parallel (auto-detects CPU cores)
make test-fast

# Tests are automatically isolated using:
# - Separate test databases per worker
# - Docker container orchestration
# - Proper resource cleanup
```

#### Database Test Fixtures

Enhanced database fixtures provide isolated test environments:

```python
# Use async database fixture for integration tests
async def test_database_operation(async_db_session):
    # Each test gets its own transaction
    # Automatically rolled back after test
    result = await create_payment(async_db_session, amount=100)
    assert result.status == "pending"

# Transactional fixtures for complete isolation
async def test_with_transactional_db(transactional_db_session):
    # Changes are visible within the transaction
    # But rolled back after the test
    await create_user(transactional_db_session, name="Test")
```

#### End-to-End Integration Tests

Comprehensive integration tests verify the full application stack:

```python
# Test complete request flow through all middleware
async def test_full_stack_request(client_with_db):
    response = await client_with_db.get("/health")

    # Verifies:
    # - Security headers applied
    # - Correlation ID generated
    # - Request/response logged
    # - OpenTelemetry span created
    # - Database connectivity checked
```

#### Docker Integration Testing

Comprehensive Docker testing infrastructure:

```python
# Test with Docker containers
def test_postgres_container(postgres_container):
    # Container automatically started/stopped
    # Health checks ensure readiness
    assert postgres_container.is_running()
```

#### Test Randomization

Tests are automatically randomized by pytest-randomly to detect hidden dependencies:

```bash
# Run tests with random ordering (shows seed)
make test-random

# Debug with specific seed
make test-seed SEED=12345

# Disable randomization for debugging
make test-no-random
```

#### Soft Assertions

For tests with multiple related assertions, use pytest-check:

```python
import pytest_check

def test_api_response():
    with pytest_check.check:
        assert response.status_code == 200
    with pytest_check.check:
        assert response.headers["Content-Type"] == "application/json"
    with pytest_check.check:
        assert "correlation_id" in response.json()
    with pytest_check.check:
        assert response.json()["status"] == "success"
```

### Test Organization

Tests are now organized into focused modules for better maintainability:

#### Unit Test Organization

```
tests/unit/
├── api/
│   └── middleware/
│       └── request_logging/     # Modular request logging tests
│           ├── test_basic_logging.py
│           ├── test_middleware_configuration.py
│           ├── test_request_body_logging.py
│           └── test_response_body_logging.py
└── core/
    └── config/                  # Modular configuration tests
        ├── test_database_config.py
        ├── test_get_settings.py
        ├── test_log_config.py
        ├── test_observability_config.py
        └── test_settings.py
```

#### Integration Test Organization

```
tests/integration/
└── api/
    └── error_handling/          # Comprehensive error handling tests
        ├── test_error_handler_type_errors.py
        ├── test_error_response_format.py
        ├── test_generic_exceptions.py
        ├── test_http_exceptions.py
        ├── test_tributum_errors.py
        └── test_validation_errors.py
```

### Test Environment Configuration

The project uses `pytest-env` to provide consistent test environment:

```python
# Base test environment configured in pyproject.toml [tool.pytest_env]
# Sets LOG_CONFIG__LOG_LEVEL="WARNING" for cleaner test output

# Use environment fixtures for specific scenarios:
def test_production_behavior(production_env):
    """Test with production environment settings."""
    settings = get_settings()
    assert settings.environment == "production"
```

Available environment fixtures:

- `production_env` - Production environment settings
- `development_env` - Development environment settings
- `staging_env` - Staging environment settings
- `custom_app_env` - Custom app name/version for testing
- `no_docs_env` - Disabled API documentation endpoints

### Running Tests

```bash
make test              # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-fast        # Parallel execution with xdist
make test-coverage    # With HTML report
make test-random      # With random ordering
make test-seed SEED=12345  # Debug with specific seed
make test-no-random   # Without randomization
make test-ci         # Optimized for CI environment
```

## 💻 Development Workflow

### Code Quality Pipeline

```mermaid
graph LR
    A[Write Code] --> B[Pre-commit Hooks]
    B --> C{Pass?}
    C -->|No| D[Fix Issues]
    D --> A
    C -->|Yes| E[Commit]
    E --> F[CI Pipeline]
    F --> G[Deploy]
```

### Pre-commit Hooks

1. **Format Check**: Ruff format validation
2. **Lint Check**: Ruff with ALL rule sets enabled
3. **Type Check**: MyPy strict mode
4. **Type Check (Enhanced)**: Pyright for additional type safety
5. **Complexity Check**: McCabe cyclomatic complexity (max 10)
6. **Security Scan**: Bandit, Safety, Semgrep
7. **Docstring Quality**: Pydoclint (Google style)
8. **Dead Code**: Vulture analysis
9. **Tests**: Fast test suite execution

### Development Best Practices

1. **Never bypass checks**: No `# type: ignore`, `# noqa`, or `--no-verify`
2. **Read complete files**: Always read entire files <2000 lines
3. **Follow patterns**: Check existing code before implementing
4. **Test everything**: Write tests for all new features
5. **Document code**: Google-style docstrings required

## 🎨 Developer Tools & Automation

### Claude Code Commands

Located in `.claude/commands/`:

- **`/check-git`**: Reads and understands all uncommitted changes in the git repository
- **`/check-implementation`**: Enhanced validation with test coverage, pattern adherence, and parallel test support
- **`/create-commit`**: Analyzes project changes and creates logical commits using conventional commit messaging
- **`/create-readme`**: Generate or update a comprehensive, developer-focused README with intelligent diff-based updates
- **`/create-release`**: Manages semantic versioning and changelog updates for releases
- **`/investigate-deps`**: Expert dependency investigation and integration planning
- **`/start`**: Quick project overview and context initialization
- **`/tasks-breakdown`**: Creates a series of sequential tasks with granular sub-tasks to implement features
- **`/tasks-project-analysis`**: Executes parallel analyses of project configuration and code structure
- **`/tasks-review`**: Reviews task plans to ensure they're specific to the project's technical architecture

### Isolated Development Tools

Some tools run in isolated environments to prevent dependency conflicts:

```bash
./scripts/tool safety scan    # Isolated safety
./scripts/tool semgrep .      # Isolated semgrep
```

Configuration in `pyproject.toml` under `[tool.isolated-tools]`.

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/checks.yml`

**Jobs**:

1. **quality-checks**: Comprehensive code quality validation
   - Format and lint checking with ALL Ruff rules
   - Type checking with MyPy
   - Enhanced type checking with Pyright
   - Complexity checking (McCabe max 10)
   - Security scanning (Bandit, Safety, pip-audit, Semgrep)
   - Dead code detection
   - Docstring quality validation
   - Test execution with coverage

2. **pre-commit**: Runs all pre-commit hooks with diff output

**Features**:

- Python 3.13 environment
- UV package manager with caching
- Parallel job execution
- Continue-on-error for non-critical tools

## 📋 Command Reference

### Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies and pre-commit hooks |
| `make dev` | Run FastAPI with auto-reload |
| `make run` | Run the application normally |
| `make clean` | Remove all temporary files |

### Code Quality Commands

| Command | Description |
|---------|-------------|
| `make format` | Format code with Ruff |
| `make format-check` | Check formatting without changes |
| `make lint` | Run linting checks |
| `make lint-fix` | Fix linting issues automatically |
| `make type-check` | Run MyPy type checking |
| `make pyright` | Run Pyright type checking |
| `make complexity-check` | Check McCabe cyclomatic complexity |
| `make all-checks` | Run all quality checks |

### Testing Commands

| Command | Description |
|---------|-------------|
| `make test` | Run all tests with coverage |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-coverage` | Generate HTML coverage report |
| `make test-fast` | Run tests in parallel with xdist |
| `make test-verbose` | Run with verbose output |
| `make test-failed` | Re-run only failed tests |
| `make test-random` | Run tests with random ordering |
| `make test-seed SEED=12345` | Run tests with specific seed |
| `make test-no-random` | Run tests without randomization |
| `make test-ci` | Run tests optimized for CI environment |

### Security Commands

| Command | Description |
|---------|-------------|
| `make security` | Run all security checks |
| `make security-bandit` | Run Bandit AST scanner |
| `make security-safety` | Check for vulnerabilities |
| `make security-pip-audit` | Audit Python packages |
| `make security-semgrep` | Static analysis |

### Database Commands

| Command | Description |
|---------|-------------|
| `make migrate-create MSG="description"` | Create new migration |
| `make migrate-up` | Apply pending migrations |
| `make migrate-down` | Rollback last migration |
| `make migrate-check` | Check for model changes |
| `make migrate-history` | Show migration history |
| `make migrate-current` | Show current revision |

### Docker Commands

| Command | Description |
|---------|-------------|
| `make docker-build` | Build all Docker images |
| `make docker-build-production` | Build production image |
| `make docker-build-dev` | Build development image |
| `make docker-up` | Start containers (production mode) |
| `make docker-up-dev` | Start containers (dev mode with hot-reload) |
| `make docker-down` | Stop all containers |
| `make docker-clean` | Remove containers and volumes |
| `make docker-logs` | View container logs |
| `make docker-shell` | Shell into API container |
| `make docker-psql` | Connect to PostgreSQL |
| `make docker-test` | Run tests in Docker |
| `make docker-migrate` | Run migrations in Docker |

### Code Analysis Commands

| Command | Description |
|---------|-------------|
| `make dead-code` | Find unused code |
| `make dead-code-report` | Generate detailed report |
| `make docstring-check` | Check all docstrings |
| `make docstring-quality` | Validate docstring format |
| `make pylint-check` | Check for code issues |

## 📦 Version Management & Release Workflow

Uses [Semantic Versioning](https://semver.org/) with automated changelog tracking.

### Development Workflow

1. **Develop & Commit**: Use `/commit` - automatically updates CHANGELOG.md
2. **Push**: Regular `git push` after commits
3. **Release**: Use `/release` when ready to tag a version

### Version Bumping

```bash
# Managed by bump-my-version
uv run bump-my-version bump patch  # 0.3.0 → 0.3.1
uv run bump-my-version bump minor  # 0.3.0 → 0.4.0
uv run bump-my-version bump major  # 0.3.0 → 1.0.0
```

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

## 🏢 Infrastructure

### Terraform Structure

```
terraform/
├── bootstrap/        # GCP project setup
├── environments/     # Environment configs
│   ├── dev/
│   ├── staging/
│   └── production/
├── main.tf          # Main infrastructure
└── backend.tf       # State management
```

### GCP Resources

- **Project**: tributum-new
- **Environments**: dev, staging, production
- **State Storage**: GCS backend with encryption
- **Cloud Run**: Container deployment support

### Infrastructure Management

```bash
# Initialize environment
cd terraform/environments/dev
terraform init

# Plan changes
terraform plan

# Apply infrastructure
terraform apply
```

### Production Deployment

The application is optimized for Google Cloud Run deployment:

- **Container Size**: 306MB multi-stage build
- **Security**: Non-root user execution
- **Port Configuration**: Respects PORT environment variable
- **Health Checks**: `/health` endpoint for container orchestration
- **Database Migrations**: Run as separate Cloud Build step

Example Cloud Build configuration:

```yaml
steps:
  # Run migrations
  - name: 'gcr.io/$PROJECT_ID/tributum:$COMMIT_SHA'
    entrypoint: 'bash'
    args: ['/app/docker/scripts/migrate.sh']
    env:
      - 'DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://...'

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'tributum', '--image=gcr.io/$PROJECT_ID/tributum:$COMMIT_SHA']
```

## 🐳 Docker Infrastructure

### Docker Development Workflow

The project includes comprehensive Docker infrastructure for both development and production environments:

```bash
# Quick start for development
make docker-up-dev      # Start with hot-reload
make docker-logs        # View logs
make docker-shell       # Shell into container
make docker-psql        # PostgreSQL CLI
make docker-down        # Stop everything
```

### Docker Architecture

```
docker/
├── app/
│   ├── Dockerfile          # Production multi-stage build
│   └── Dockerfile.dev      # Development with hot-reload
├── postgres/
│   └── init.sql           # Database initialization
└── scripts/
    ├── entrypoint.sh      # Container startup script
    ├── migrate.sh         # Migration runner
    └── wait-for-postgres.sh  # Health check utility
```

### Production Docker Image

Multi-stage build optimized for Cloud Run:

- **Base**: Python 3.13-slim
- **Size**: ~306MB final image
- **Security**: Non-root user (appuser)
- **Features**:
  - Dependency caching
  - Source code isolation
  - Health check support
  - PORT environment variable

### Development Docker Image

Optimized for local development:

- **Hot Reload**: Volume-mounted source code
- **Debug Tools**: Full development dependencies
- **Database**: Auto-configured PostgreSQL
- **Features**:
  - Instant code changes
  - Debugger support
  - Test execution
  - Migration tools

### Docker Compose Configuration

#### Production Mode (`docker-compose.yml`)

```yaml
services:
  api:
    image: tributum:production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://...
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:17-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tributum"]
```

#### Development Mode (`docker-compose.dev.yml`)

```yaml
services:
  api:
    build:
      context: .
      dockerfile: docker/app/Dockerfile.dev
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
```

### Database Container Features

- **Test Database**: Automatically created `tributum_test`
- **Parallel Testing**: Worker databases for pytest-xdist
- **Health Checks**: Wait scripts ensure readiness
- **Permissions**: Full grants to tributum user
- **Init Script**: Custom initialization for test support

### Docker Best Practices

1. **No Hardcoded Configs**: All configuration via environment variables
2. **Health Checks**: Database availability handled by `pool_pre_ping`
3. **Migrations**: Run as separate container/job, not in entrypoint
4. **Logging**: JSON format for container environments
5. **Signals**: Proper handling for graceful shutdown

### Common Docker Operations

```bash
# Build images
make docker-build          # All images
make docker-build-production  # Production only
make docker-build-dev      # Development only

# Development workflow
make docker-up-dev         # Start development
make docker-migrate        # Run migrations
make docker-test          # Run tests in container

# Debugging
make docker-logs          # View all logs
make docker-shell         # Shell access
make docker-psql          # Database access

# Cleanup
make docker-down          # Stop containers
make docker-clean         # Remove everything
```

## 💾 Database Configuration

### Database Stack

- **PostgreSQL**: Primary database with async support
- **SQLAlchemy 2.0+**: Modern ORM with async capabilities
- **asyncpg**: High-performance PostgreSQL driver
- **Alembic**: Database migration management

### Configuration Options

```python
class DatabaseConfig:
    database_url: str  # postgresql+asyncpg://user:pass@host:port/db
    pool_size: int = 10  # Connection pool size (1-100)
    max_overflow: int = 5  # Additional connections above pool_size (0-50)
    pool_timeout: float = 30.0  # Connection acquisition timeout
    pool_pre_ping: bool = True  # Test connections before use
    echo: bool = False  # SQL statement logging (debug only)
```

### Environment Variables

```bash
# Database Configuration
DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db
DATABASE_CONFIG__POOL_SIZE=10
DATABASE_CONFIG__MAX_OVERFLOW=5
DATABASE_CONFIG__POOL_TIMEOUT=30.0
DATABASE_CONFIG__POOL_PRE_PING=true
DATABASE_CONFIG__ECHO=false

# Note: In test environment, the database URL automatically points to tributum_test
```

### Database Features

- **Async Operations**: Full async/await support with asyncpg
- **Connection Pooling**: Efficient connection management
- **Health Checks**: Pre-ping connections to detect failures
- **Test Isolation**: Separate test database with automatic URL generation
- **Parallel Testing**: Worker-specific databases for pytest-xdist
- **URL Validation**: Enforces `postgresql+asyncpg://` driver for async support
- **Lifecycle Management**: Proper startup/shutdown in FastAPI lifespan

### Database Migrations with Alembic

The project uses Alembic for database schema management with async support:

#### Migration Commands

```bash
# Create a new migration
make migrate-create MSG="add users table"

# Apply all pending migrations
make migrate-up

# Rollback last migration
make migrate-down

# Check for model changes
make migrate-check

# Show migration history
make migrate-history

# Show current revision
make migrate-current
```

#### Migration Configuration

- **Location**: `src/infrastructure/database/migrations/`
- **Async Support**: Configured for asyncpg driver
- **Auto-generation**: Detects model changes automatically
- **Naming Convention**: SQL naming conventions for constraints
- **Initial Migration**: Empty migration created as starting point

#### Docker Migration Support

```bash
# Run migrations in Docker container
make docker-migrate

# Migrations run in separate container
# Never in application entrypoint
```

### Test Database Infrastructure

The project includes robust test database management:

```python
# Database fixtures provide isolated test environments
@pytest.fixture
async def async_db_session():
    """Provides isolated async database session for tests."""
    # Each test runs in its own transaction
    # Automatically rolled back after test completion

# Parallel test support
# Worker databases automatically selected based on xdist worker ID
# Example: gw0 uses tributum_test_gw0, gw1 uses tributum_test_gw1
```

## ⚙️ Configuration Management

### Environment Variables

```bash
# Core Settings
APP_NAME=tributum
APP_VERSION=0.3.0
ENVIRONMENT=development  # development|staging|production
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000  # Overridden by PORT in Cloud Run
DOCS_URL=/docs
REDOC_URL=/redoc
OPENAPI_URL=/openapi.json

# Logging - Enhanced Configuration
LOG_CONFIG__LOG_LEVEL=INFO
LOG_CONFIG__LOG_FORMAT=console  # console|json
LOG_CONFIG__RENDER_JSON_LOGS=false  # auto-true in staging/production
LOG_CONFIG__EXCLUDED_PATHS=["/health", "/metrics"]
LOG_CONFIG__SENSITIVE_FIELDS=["password", "token", "secret", "api_key"]
LOG_CONFIG__ENABLE_SQL_LOGGING=false
LOG_CONFIG__SLOW_QUERY_THRESHOLD_MS=100
LOG_CONFIG__ENABLE_PERFORMANCE_PROCESSOR=false
LOG_CONFIG__ENABLE_ENVIRONMENT_PROCESSOR=true
LOG_CONFIG__ENABLE_ERROR_CONTEXT_PROCESSOR=true
LOG_CONFIG__LOG_REQUEST_BODY=false
LOG_CONFIG__LOG_RESPONSE_BODY=false
LOG_CONFIG__MAX_BODY_LOG_SIZE=10240

# Observability
OBSERVABILITY_CONFIG__ENABLE_TRACING=false
OBSERVABILITY_CONFIG__SERVICE_NAME=tributum
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=  # Optional GCP project
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=1.0  # 0.0 to 1.0

# Database
DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db
DATABASE_CONFIG__POOL_SIZE=10
DATABASE_CONFIG__MAX_OVERFLOW=5
DATABASE_CONFIG__POOL_TIMEOUT=30.0
DATABASE_CONFIG__POOL_PRE_PING=true
DATABASE_CONFIG__ECHO=false

# Cloud Run Compatibility
PORT=8000  # Automatically respected when set
```

### Configuration Validation

All configs validated at startup using Pydantic Settings v2:

- Type validation
- Required field checking
- Nested configuration support
- Environment-specific defaults
- Automatic JSON logging for staging/production environments

### Docker Configuration

The application uses standard environment variables without Docker-specific settings:

- **No SKIP_DB_WAIT**: Database availability handled by `pool_pre_ping`
- **No RUN_MIGRATIONS**: Migrations run as separate container/job
- **PORT Support**: Automatically uses PORT env var for Cloud Run
- **Unified Config**: Same environment variables for local and Docker

## 📁 Project Structure

```
src/
├── api/                    # HTTP layer
│   ├── main.py            # FastAPI app with lifespan management
│   ├── constants.py       # API-specific constants (HTTP codes, limits)
│   ├── middleware/        # ASGI middleware
│   │   ├── error_handler.py      # Global exception handling
│   │   ├── request_context.py    # Correlation ID management
│   │   ├── request_logging.py    # Request/response logging
│   │   └── security_headers.py   # Security headers
│   ├── routes/            # API endpoints
│   │   └── health.py     # Health check endpoint
│   ├── schemas/           # Pydantic models
│   │   └── errors.py     # Error response schemas
│   └── utils/
│       └── responses.py   # ORJSONResponse
├── core/                  # Shared utilities
│   ├── config.py         # Pydantic Settings with enhanced LogConfig
│   ├── constants.py      # Core layer constants (logging, security)
│   ├── context.py        # Request context
│   ├── error_context.py  # Error enrichment
│   ├── exceptions.py     # Exception hierarchy
│   ├── logging.py        # Structured logging with context management
│   ├── observability.py  # OpenTelemetry setup
│   └── types.py          # Type definitions
├── domain/               # Business logic (DDD structure prepared)
└── infrastructure/       # Data layer
    ├── constants.py      # Infrastructure constants (DB settings)
    └── database/         # Database infrastructure
        ├── base.py       # Base model with timestamps
        ├── dependencies.py # FastAPI database dependencies
        ├── migrations/   # Alembic migrations
        │   ├── alembic.ini
        │   ├── env.py
        │   ├── script.py.mako
        │   └── versions/
        ├── repository.py # Extended generic repository pattern
        └── session.py    # Async session management

tests/
├── unit/                 # Isolated unit tests
│   ├── api/
│   │   └── middleware/
│   │       └── request_logging/  # Modular request logging tests
│   └── core/
│       └── config/      # Modular configuration tests
├── integration/          # Integration tests with tracing
│   ├── api/
│   │   └── error_handling/       # Comprehensive error tests
│   ├── test_database_example.py  # Database integration examples
│   ├── test_docker_compose.py    # Docker orchestration tests
│   ├── test_fixture_isolation.py # Database fixture isolation
│   └── test_full_stack.py        # End-to-end stack tests
├── fixtures/             # Environment-specific test fixtures
│   ├── test_database_fixtures.py # Database test utilities
│   └── test_docker_fixtures.py   # Docker container management
└── conftest.py          # Shared fixtures with auto-clearing cache

docker/
├── app/                 # Application containers
│   ├── Dockerfile       # Production multi-stage build
│   └── Dockerfile.dev   # Development with hot-reload
├── postgres/            # PostgreSQL development setup
│   └── init.sql        # Test database initialization
└── scripts/            # Container helper scripts
    ├── entrypoint.sh   # Minimal startup script
    ├── migrate.sh      # Migration runner
    └── wait-for-postgres.sh  # Database readiness check
```

## 🔍 Troubleshooting Guide

### Common Issues

#### Import Errors

```bash
# Ensure Python 3.13 is active
python --version

# Update dependencies
uv sync --all-extras --dev
```

#### Type Errors

```bash
# Clear MyPy cache
rm -rf .mypy_cache

# Install type stubs
uv run mypy --install-types

# Check Pyright configuration
uv run pyright --version
```

#### Pre-commit Failures

```bash
# Update hooks
uv run pre-commit clean
uv run pre-commit install --install-hooks

# Run manually
make pre-commit
```

#### Test Failures

```bash
# Run specific test
uv run pytest tests/unit/core/test_config.py -v

# Debug with print statements
uv run pytest -s

# Debug random test failures
uv run pytest --randomly-seed=12345

# Debug parallel test issues
uv run pytest -n 1  # Run single-threaded
```

#### Database Connection Issues

```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -U postgres -c "\l" | grep tributum

# Test connection with async driver
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://tributum:tributum_pass@localhost:5432/tributum_db'))"

# For parallel tests, verify worker databases
psql -U postgres -c "\l" | grep tributum_test_gw
```

#### Docker Issues

```bash
# Check Docker daemon
docker info

# View container logs
make docker-logs

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Database connection in Docker
docker exec -it tributum-postgres psql -U tributum -d tributum_db

# Rebuild images
make docker-clean
make docker-build
```

#### Migration Issues

```bash
# Check current revision
make migrate-current

# Generate migration SQL
cd src/infrastructure/database
alembic upgrade head --sql

# Manual migration
cd src/infrastructure/database
alembic upgrade head

# Rollback
alembic downgrade -1
```

#### Parallel Test Issues

```bash
# Check if running with xdist
uv run pytest --collect-only | grep "gw"

# Force single-threaded execution
make test-no-random

# Check Docker containers for tests
docker ps | grep postgres

# Verify test database permissions
psql -U tributum -d tributum_test -c "SELECT 1;"
```

#### Tracing Issues

```bash
# Enable debug logging for OpenTelemetry
export OTEL_LOG_LEVEL=debug
export LOG_CONFIG__LOG_LEVEL=DEBUG

# Verify GCP credentials
gcloud auth application-default login
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_CONFIG__LOG_LEVEL=DEBUG
make dev
```

## 🌐 API Endpoints

### Health Check Endpoint

**GET** `/health`

Returns the health status of the application and its dependencies.

#### Response Format

```json
{
  "status": "healthy",
  "database": true
}
```

#### Status Codes

- **200 OK**: Application is healthy
- **503 Service Unavailable**: Application is unhealthy (database unavailable)

#### Features

- Database connectivity check with fallback
- OpenTelemetry span creation for monitoring
- Correlation ID propagation
- Used by:
  - Docker health checks
  - Kubernetes liveness/readiness probes
  - Cloud Run health checks
  - Load balancer health checks

#### Example Usage

```bash
# Check health
curl http://localhost:8000/health

# With correlation ID
curl -H "X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000" \
     http://localhost:8000/health
```

### Info Endpoint

**GET** `/info`

Returns application metadata and configuration information.

#### Response Format

```json
{
  "app_name": "tributum",
  "app_version": "0.3.0",
  "environment": "development",
  "debug": true,
  "docs_url": "/docs",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### API Documentation

Interactive API documentation is available at:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

Documentation can be disabled by setting environment variables to empty strings.

## ✅ Current Implementation Status

### Implemented Features

#### Core Infrastructure

- FastAPI application with automatic OpenAPI documentation
- Pydantic Settings v2 configuration with nested support
- Domain-driven design directory structure
- High-performance JSON serialization with ORJSON
- **Integrated middleware stack with proper ordering**
- **Health check endpoint with database connectivity verification**
- **Cloud Run compatibility with PORT environment variable**

#### Database Infrastructure

- **Database configuration system** with async PostgreSQL support
- **Connection pooling** with configurable pool size and overflow
- **Health checks** with pre-ping connection testing
- **Test database isolation** with automatic URL generation
- **Parallel test database support** with worker-specific databases
- **Docker infrastructure** for PostgreSQL development
- **Database dependencies**: SQLAlchemy 2.0+, asyncpg, Alembic, greenlet
- **Base model** with automatic timestamps (created_at, updated_at)
- **Extended generic repository pattern** with full CRUD operations and filtering
- **FastAPI dependency injection** for database sessions
- **Sequential BigInteger IDs** optimized for PostgreSQL
- **Alembic migration system** with async support and initial migration
- **Database lifecycle management** in FastAPI lifespan context

#### Exception & Error Handling

- Comprehensive exception hierarchy with severity levels
- Global exception handlers for all error types
- Standardized error responses with correlation IDs
- Automatic context capture and sanitization
- Debug information in development mode
- Integration with OpenTelemetry span error tracking

#### Logging & Observability

- Structured logging with structlog (exc_info formatting configured)
- Automatic correlation ID propagation
- Request/response body logging with sanitization
- Console and JSON formatters
- Sensitive data redaction
- Automatic JSON logging for staging/production environments
- **OpenTelemetry distributed tracing with GCP Cloud Trace export**
- **Automatic HTTP request instrumentation**
- **SQLAlchemy query instrumentation** (prepared for database operations)
- **Configurable trace sampling**
- **Error context enrichment in spans**
- **Enhanced logging configuration** with path exclusion, SQL logging, and performance processors
- **Advanced context management** with bind/unbind operations

#### Middleware Stack

- **SecurityHeadersMiddleware** for security headers
- **RequestContextMiddleware** for correlation IDs
- **RequestLoggingMiddleware** for observability
- **Global error handling** with proper exception propagation
- **OpenTelemetry instrumentation** middleware
- **Pure ASGI implementation** for performance

#### Docker Infrastructure

- **Production Docker image** with multi-stage build (~306MB)
- **Development Docker image** with hot-reload support
- **Docker Compose** for local development and testing
- **Database initialization** scripts for test support
- **Health check utilities** for container readiness
- **Migration support** as separate container/job
- **Comprehensive Makefile commands** for Docker operations

#### Testing Infrastructure

- **Parallel test execution** with pytest-xdist
- **Database test fixtures** with transaction isolation
- **Docker container fixtures** for integration testing
- **Worker-specific test databases** for parallel execution
- **Automatic database cleanup** after tests
- **Health check utilities** for container readiness
- **Integration test examples** for database operations
- **100% test coverage** with pytest-mock standardization
- **Enhanced test output** with pytest-rich
- **Comprehensive end-to-end integration tests** for full stack validation
- **Transactional database fixtures** for complete test isolation
- **Modular test organization** for better maintainability

#### Development Experience

- Comprehensive pre-commit hooks with ALL Ruff rules enabled
- McCabe cyclomatic complexity checking (max 10)
- Strict code quality enforcement (Ruff, MyPy, Pyright)
- Security scanning pipeline
- 100% test coverage achieved with pytest-mock migration
- pytest-env integration for streamlined test environment management
- pytest-randomly for detecting test interdependencies
- pytest-check for soft assertions in tests
- pytest-rich with xdist compatibility
- Claude Code automation commands including `/investigate-deps`, `/start`, `/review-task`, `/task-analysis`, and enhanced `/check-implementation`
- **Docker development workflow** with hot-reload
- **Parallel test execution** for faster CI/CD
- **Pyright type checking** for enhanced IDE support

#### CI/CD & Infrastructure

- GitHub Actions workflow for quality checks with Pyright
- Terraform infrastructure for GCP
- Multi-environment support (dev/staging/prod)
- Automated version management (v0.3.0)
- Changelog automation
- **Docker support** for CI/CD pipelines
- **Cloud Run deployment** compatibility

### Architecture Components

#### API Layer (`src/api/`)

- Main FastAPI application with ORJSONResponse
- **Lifespan management** for startup/shutdown
- **Integrated middleware stack**
- **Health check route**
- Error response schemas
- Utility functions
- **Layer-specific constants** for HTTP codes, limits, and content types

#### Core Layer (`src/core/`)

- Configuration management with **enhanced LogConfig**, **ObservabilityConfig**, and **DatabaseConfig**
- Exception definitions with span integration
- Logging setup with exc_info formatting and **advanced context management**
- Context management
- **Layer-specific constants** for logging and security patterns
- Type definitions
- **OpenTelemetry tracing utilities**

#### Domain Layer (`src/domain/`)

- Directory structure prepared for DDD implementation
- Ready for business logic modules

#### Infrastructure Layer (`src/infrastructure/`)

- **Database infrastructure** with async PostgreSQL support
- **Base model** with timestamps and naming conventions
- **Extended generic repository pattern** with filtering
- **Session management** with connection pooling
- **FastAPI dependencies** for database injection
- **Alembic migrations** with async configuration
- **Layer-specific constants** for database settings

#### Test Suite (`tests/`)

- Unit tests with 100% coverage achieved
- Integration tests for API endpoints
- **Integration tests for distributed tracing**
- **Database infrastructure tests**
- **Docker container integration tests**
- **Comprehensive end-to-end stack tests**
- **Modular test organization** into focused modules
- Environment-specific test fixtures
- Shared fixtures with auto-clearing cache
- Async test support
- Migrated to pytest-mock for cleaner mocking
- pytest-env for centralized test configuration
- pytest-randomly for randomized test execution
- pytest-check for comprehensive test failure reporting
- pytest-xdist for parallel test execution
- **Database test fixtures** for isolated testing
- **Docker test fixtures** for container management

<!-- README-METADATA
Last Updated: 2025-06-25T18:45:00Z
Last Commit: d501d56
Schema Version: 2.0
Sections: {
  "overview": {"hash": "updated-0563fb4", "manual": false},
  "tech-stack": {"hash": "updated-76a15ba", "manual": false},
  "quick-start": {"hash": "updated-76a15ba", "manual": false},
  "architecture": {"hash": "updated-d501d56", "manual": false},
  "frameworks": {"hash": "updated-d501d56", "manual": false},
  "observability": {"hash": "updated-da0a58e", "manual": false},
  "security": {"hash": "updated-5479972", "manual": false},
  "testing": {"hash": "updated-d501d56", "manual": false},
  "workflow": {"hash": "updated-0563fb4", "manual": false},
  "tools": {"hash": "updated-d501d56", "manual": false},
  "cicd": {"hash": "updated-0563fb4", "manual": false},
  "commands": {"hash": "updated-76a15ba", "manual": false},
  "version": {"hash": "updated-da0a58e", "manual": false},
  "infrastructure": {"hash": "updated-76a15ba", "manual": false},
  "docker": {"hash": "updated-76a15ba", "manual": false},
  "database": {"hash": "updated-76a15ba", "manual": false},
  "config": {"hash": "updated-d501d56", "manual": false},
  "structure": {"hash": "updated-d501d56", "manual": false},
  "troubleshooting": {"hash": "updated-76a15ba", "manual": false},
  "api-endpoints": {"hash": "new-76a15ba", "manual": false},
  "status": {"hash": "updated-d501d56", "manual": false}
}
-->
