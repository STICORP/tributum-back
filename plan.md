# Cross-Cutting Concerns Implementation Plan

## Context and Important Instructions

This plan was created to implement robust cross-cutting concerns for the Tributum backend project. Key decisions and constraints:

1. **Focus on Cross-Cutting Concerns Only**: This plan specifically addresses infrastructure concerns (error handling, logging, middleware, security headers, request/response logging, database setup with base repository pattern). Domain-specific features are NOT part of this plan.

2. **Technology Stack Decisions**:
   - Database: PostgreSQL with SQLAlchemy 2.0 (async) and Alembic for migrations
   - Observability: OpenTelemetry with GCP integration (Cloud Trace, Cloud Monitoring)
   - Logging: Structured JSON logging with correlation ID support
   - API Framework: FastAPI with Pydantic v2

3. **Architecture Decisions**:
   - **API-specific middleware** stays in `src/api/middleware/` (security headers, request logging, etc.)
   - **Shared infrastructure** goes in `src/core/` (exceptions, logging setup, context, observability)
   - **Database infrastructure** goes in `src/infrastructure/database/`
   - Repository pattern for data access abstraction

4. **Implementation Constraints**:
   - Each task must be small, self-contained, testable, and committable
   - Tasks are ordered with clear dependencies
   - Every component must have tests with clear acceptance criteria
   - The implementation can be done with cleared context - each task has all needed information

5. **Testing Strategy**:
   - Unit tests for each component in isolation
   - Integration tests for middleware and database
   - Use in-memory SQLite for unit tests, real PostgreSQL for integration tests
   - Every middleware must be tested both in isolation and integrated

## Implementation Order and Dependencies

The tasks are organized in phases with clear dependencies:
- Phase 1 (Exceptions) → Foundation for all error handling
- Phase 2 (Logging) → Required by middleware and services
- Phase 3 (Context) → Required for correlation IDs
- Phase 4 (API Middleware) → Depends on 1, 2, 3
- Phase 5 (OpenTelemetry) → Can be done after context setup
- Phase 6 (Database) → Independent but needed before integration
- Phase 7 (Integration) → Requires all previous phases
- Phase 8 (Documentation) → Final phase

## Detailed Implementation Plan

### Phase 1: Exception Infrastructure (Foundation)

#### Task 1.1: Create Base Exception Class
**File**: `src/core/exceptions.py`
**Implementation**:
- Create `TributumError` base class with error_code and message
- Add `__str__` and `__repr__` methods
**Tests**: `tests/unit/core/test_exceptions.py`
- Test exception creation with code and message
- Test string representation
**Acceptance Criteria**:
- Exception stores error_code and message
- Can be raised and caught
- String representation includes both code and message

#### Task 1.2: Create Exception Error Codes Enum
**File**: `src/core/exceptions.py`
**Implementation**:
- Create `ErrorCode` enum with initial codes (INTERNAL_ERROR, VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED)
- Document each error code
**Tests**: Update `tests/unit/core/test_exceptions.py`
- Test all enum values are unique
- Test enum can be used with base exception
**Acceptance Criteria**:
- All error codes have unique values
- Error codes follow consistent naming pattern

#### Task 1.3: Create Specialized Exception Classes
**File**: `src/core/exceptions.py`
**Implementation**:
- Create `ValidationError(TributumError)`
- Create `NotFoundError(TributumError)`
- Create `UnauthorizedError(TributumError)`
- Create `BusinessRuleError(TributumError)`
**Tests**: Update `tests/unit/core/test_exceptions.py`
- Test each exception type with default error codes
- Test inheritance chain
**Acceptance Criteria**:
- Each exception has appropriate default error code
- All inherit from TributumError

#### Task 1.4: Create Error Response Model
**File**: `src/api/schemas/errors.py`
**Implementation**:
- Create `ErrorResponse` Pydantic model with fields: error_code, message, details (optional), correlation_id (optional)
- Add response examples
**Tests**: `tests/unit/api/schemas/test_errors.py`
- Test model validation
- Test JSON serialization
**Acceptance Criteria**:
- Model validates required fields
- Can serialize to JSON with correct structure

### Phase 2: Logging Infrastructure

#### Task 2.1: Create Logging Configuration
**File**: `src/core/config.py`
**Implementation**:
- Add `LogConfig` nested class in Settings
- Add fields: log_format (json/text), log_handlers, log_file_path
- Add environment variable support
**Tests**: Update `tests/unit/core/test_config.py`
- Test default values
- Test environment override
**Acceptance Criteria**:
- Can configure JSON or text format
- File path is optional

#### Task 2.2: Create JSON Log Formatter
**File**: `src/core/logging.py`
**Implementation**:
- Create `JsonFormatter` class
- Include timestamp, level, logger_name, message, extra fields
- Handle exception formatting
**Tests**: `tests/unit/core/test_logging.py`
- Test JSON output structure
- Test exception formatting
- Test extra fields inclusion
**Acceptance Criteria**:
- Outputs valid JSON
- Includes all required fields
- Handles exceptions without crashing

#### Task 2.3: Create Logger Factory
**File**: `src/core/logging.py`
**Implementation**:
- Create `setup_logging()` function
- Create `get_logger(name)` function
- Support both JSON and text formats based on config
**Tests**: Update `tests/unit/core/test_logging.py`
- Test logger creation
- Test format switching
- Test multiple logger instances
**Acceptance Criteria**:
- Returns configured logger instances
- Respects format configuration
- Loggers are cached

#### Task 2.4: Create Logging Context Utilities
**File**: `src/core/logging.py`
**Implementation**:
- Create `LoggingContext` class for adding context fields
- Create context manager for temporary logging context
**Tests**: Update `tests/unit/core/test_logging.py`
- Test context addition/removal
- Test nested contexts
**Acceptance Criteria**:
- Can add/remove context fields
- Context is thread-safe
- Supports nesting

### Phase 3: Request Context Infrastructure

#### Task 3.1: Create Correlation ID Generator
**File**: `src/core/context.py`
**Implementation**:
- Create `generate_correlation_id()` using UUID4
- Create `CORRELATION_ID_HEADER` constant
**Tests**: `tests/unit/core/test_context.py`
- Test ID format
- Test uniqueness
**Acceptance Criteria**:
- Generates valid UUID4
- Each call produces unique ID

#### Task 3.2: Create Request Context Storage
**File**: `src/core/context.py`
**Implementation**:
- Create `RequestContext` class using contextvars
- Add correlation_id storage and retrieval
- Add method to get current context
**Tests**: Update `tests/unit/core/test_context.py`
- Test context storage/retrieval
- Test context isolation between async tasks
**Acceptance Criteria**:
- Context is isolated per request
- Works with async/await
- Can retrieve None if not set

#### Task 3.3: Create Context Middleware
**File**: `src/api/middleware/request_context.py`
**Implementation**:
- Create `RequestContextMiddleware` class
- Extract or generate correlation ID
- Set context for request lifetime
- Add correlation ID to response headers
**Tests**: `tests/unit/api/middleware/test_request_context.py`
- Test correlation ID extraction from header
- Test ID generation when missing
- Test response header addition
**Acceptance Criteria**:
- Uses existing correlation ID if provided
- Generates new ID if missing
- Adds ID to response headers

### Phase 4: API Middleware

#### Task 4.1: Create Security Headers Middleware
**File**: `src/api/middleware/security_headers.py`
**Implementation**:
- Create `SecurityHeadersMiddleware` class
- Add X-Content-Type-Options: nosniff
- Add X-Frame-Options: DENY
- Add X-XSS-Protection: 1; mode=block
- Add Strict-Transport-Security (configurable)
**Tests**: `tests/unit/api/middleware/test_security_headers.py`
- Test each header is added
- Test header values
**Acceptance Criteria**:
- All security headers present in responses
- Headers have correct values

#### Task 4.2: Create Request Logging Middleware
**File**: `src/api/middleware/request_logging.py`
**Implementation**:
- Create `RequestLoggingMiddleware` class
- Log method, path, correlation_id on request
- Log status_code, duration on response
- Implement sensitive path filtering
**Tests**: `tests/unit/api/middleware/test_request_logging.py`
- Test request logging format
- Test response logging format
- Test sensitive path filtering
**Acceptance Criteria**:
- Logs include correlation ID
- Duration is calculated correctly
- Sensitive paths are filtered

#### Task 4.3: Create Global Exception Handler
**File**: `src/api/middleware/error_handler.py`
**Implementation**:
- Create exception handler for `TributumError`
- Create handler for `RequestValidationError`
- Create handler for generic `Exception`
- Include correlation ID in error responses
**Tests**: `tests/integration/api/test_error_handling.py`
- Test each exception type handling
- Test error response format
- Test correlation ID inclusion
**Acceptance Criteria**:
- Returns correct HTTP status codes
- Error format matches ErrorResponse model
- No sensitive data in responses

### Phase 5: OpenTelemetry Setup

#### Task 5.1: Add OpenTelemetry Dependencies
**File**: `pyproject.toml`
**Implementation**:
- Add opentelemetry-api
- Add opentelemetry-sdk
- Add opentelemetry-instrumentation-fastapi
- Add opentelemetry-instrumentation-sqlalchemy
- Add opentelemetry-exporter-gcp-trace
**Tests**: Run `uv sync` successfully
**Acceptance Criteria**:
- All packages install without conflicts
- Versions are compatible

#### Task 5.2: Create Observability Configuration
**File**: `src/core/config.py`
**Implementation**:
- Add `ObservabilityConfig` to Settings
- Add fields: enable_tracing, service_name, gcp_project_id, trace_sample_rate
**Tests**: Update `tests/unit/core/test_config.py`
- Test default values
- Test environment override
**Acceptance Criteria**:
- Can enable/disable tracing
- Sample rate between 0.0 and 1.0

#### Task 5.3: Create Tracing Setup
**File**: `src/core/observability.py`
**Implementation**:
- Create `setup_tracing()` function
- Configure GCP trace exporter
- Set up trace provider with sampling
- Create `get_tracer()` function
**Tests**: `tests/unit/core/test_observability.py`
- Test setup with tracing disabled
- Test tracer creation
**Acceptance Criteria**:
- Tracing can be disabled
- Returns configured tracer
- No errors when GCP not available

#### Task 5.4: Instrument FastAPI
**File**: `src/api/main.py`
**Implementation**:
- Call `setup_tracing()` on startup
- Add FastAPI instrumentation
- Ensure correlation ID propagation
**Tests**: `tests/integration/api/test_tracing.py`
- Test spans are created for requests
- Test correlation ID in spans
**Acceptance Criteria**:
- Each request creates a span
- Spans include correlation ID
- Parent-child relationships correct

### Phase 6: Database Infrastructure

#### Task 6.1: Add Database Dependencies
**File**: `pyproject.toml`
**Implementation**:
- Add sqlalchemy[asyncio]>=2.0
- Add asyncpg (PostgreSQL async driver)
- Add alembic>=1.13
- Add greenlet (for async SQLAlchemy)
**Tests**: Run `uv sync` successfully
**Acceptance Criteria**:
- All packages install
- Versions are compatible

#### Task 6.2: Create Database Configuration
**File**: `src/core/config.py`
**Implementation**:
- Add `DatabaseConfig` to Settings
- Add fields: database_url, pool_size, max_overflow, pool_timeout
- Add test database URL support
**Tests**: Update `tests/unit/core/test_config.py`
- Test default values
- Test URL parsing
**Acceptance Criteria**:
- Supports PostgreSQL URLs
- Pool settings have sensible defaults

#### Task 6.3: Create Base Model
**File**: `src/infrastructure/database/base.py`
**Implementation**:
- Create SQLAlchemy declarative base
- Create `BaseModel` with id (UUID), created_at, updated_at
- Add naming convention for constraints
**Tests**: `tests/unit/infrastructure/database/test_base.py`
- Test model creation
- Test timestamp defaults
**Acceptance Criteria**:
- UUID primary keys work
- Timestamps auto-populate
- Naming conventions applied

#### Task 6.4: Create Async Session Factory
**File**: `src/infrastructure/database/session.py`
**Implementation**:
- Create async engine with connection pool
- Create async session factory
- Create `get_async_session` context manager
**Tests**: `tests/unit/infrastructure/database/test_session.py`
- Test session creation
- Test connection pooling
- Test context manager cleanup
**Acceptance Criteria**:
- Sessions are async
- Pool respects configuration
- Proper cleanup on exit

#### Task 6.5: Create Database Dependencies
**File**: `src/infrastructure/database/dependencies.py`
**Implementation**:
- Create `get_db` async dependency for FastAPI
- Ensure proper session lifecycle
- Add typing for better IDE support
**Tests**: `tests/unit/infrastructure/database/test_dependencies.py`
- Test dependency injection
- Test session cleanup
**Acceptance Criteria**:
- Works with FastAPI Depends
- Sessions are closed properly
- Type hints work correctly

#### Task 6.6: Create Base Repository
**File**: `src/infrastructure/database/repository.py`
**Implementation**:
- Create `BaseRepository[T]` generic class
- Implement `get_by_id(id: UUID) -> T | None`
- Implement `get_all(skip: int, limit: int) -> list[T]`
- Implement `create(obj: T) -> T`
**Tests**: `tests/unit/infrastructure/database/test_repository.py`
- Test each CRUD operation
- Test with mock model
**Acceptance Criteria**:
- Generic typing works
- All methods are async
- Handles None cases properly

#### Task 6.7: Extend Base Repository
**File**: `src/infrastructure/database/repository.py`
**Implementation**:
- Add `update(id: UUID, data: dict) -> T | None`
- Add `delete(id: UUID) -> bool`
- Add `count() -> int`
- Add `exists(id: UUID) -> bool`
**Tests**: Update `tests/unit/infrastructure/database/test_repository.py`
- Test update with partial data
- Test delete return value
- Test count accuracy
**Acceptance Criteria**:
- Update handles partial updates
- Delete returns success/failure
- Count is efficient

#### Task 6.8: Add Repository Filtering
**File**: `src/infrastructure/database/repository.py`
**Implementation**:
- Add `filter_by(**kwargs) -> list[T]`
- Add `find_one_by(**kwargs) -> T | None`
- Add query builder pattern support
**Tests**: Update `tests/unit/infrastructure/database/test_repository.py`
- Test filtering with multiple conditions
- Test find_one behavior
**Acceptance Criteria**:
- Supports multiple filter conditions
- find_one returns first match
- Efficient SQL generation

#### Task 6.9: Initialize Alembic
**Implementation**:
- Run `alembic init alembic`
- Update alembic.ini for async
- Create async migration env.py
- Update Makefile with migration commands
**Tests**: Manual verification
**Acceptance Criteria**:
- Alembic initialized
- Async migrations work
- Makefile commands work

#### Task 6.10: Create Initial Migration
**Implementation**:
- Create empty initial migration
- Test upgrade/downgrade
**Tests**: Manual verification
**Acceptance Criteria**:
- Migration runs without errors
- Can upgrade and downgrade

### Phase 7: Integration

#### Task 7.1: Wire Middleware in Correct Order
**File**: `src/api/main.py`
**Implementation**:
- Add SecurityHeadersMiddleware (first)
- Add RequestContextMiddleware
- Add RequestLoggingMiddleware
- Register exception handlers
**Tests**: `tests/integration/api/test_middleware_integration.py`
- Test middleware execution order
- Test all middleware active
**Acceptance Criteria**:
- Middleware execute in correct order
- All headers/logs present

#### Task 7.2: Add Database Lifecycle
**File**: `src/api/main.py`
**Implementation**:
- Add startup event for DB connection check
- Add shutdown event for connection cleanup
- Add health check endpoint
**Tests**: `tests/integration/api/test_lifecycle.py`
- Test startup/shutdown events
- Test health check
**Acceptance Criteria**:
- Clean startup/shutdown
- Health check reports DB status

#### Task 7.3: Create Integration Test Fixtures
**File**: `tests/conftest.py`
**Implementation**:
- Add async test database fixture
- Add database transaction rollback
- Add test client with DB
**Tests**: Self-testing through usage
**Acceptance Criteria**:
- Tests are isolated
- No test data persists
- Async tests work

#### Task 7.4: End-to-End Integration Tests
**File**: `tests/integration/test_full_stack.py`
**Implementation**:
- Test request with all middleware
- Test error handling with correlation ID
- Test database operations in request
- Test OpenTelemetry span creation
**Tests**: The tests themselves
**Acceptance Criteria**:
- Full request lifecycle works
- All components integrate
- Performance acceptable

### Phase 8: Documentation

#### Task 8.1: Document Exception Handling
**File**: `CLAUDE.md`
**Implementation**:
- Document exception hierarchy
- Add examples of raising exceptions
- Document error response format
**Acceptance Criteria**:
- Clear examples provided
- All exception types documented

#### Task 8.2: Document Logging Standards
**File**: `CLAUDE.md`
**Implementation**:
- Document log format
- Add logging best practices
- Show context usage examples
**Acceptance Criteria**:
- Format clearly explained
- Examples for common cases

#### Task 8.3: Document Database Patterns
**File**: `CLAUDE.md`
**Implementation**:
- Document repository pattern usage
- Add transaction examples
- Document migration workflow
**Acceptance Criteria**:
- Clear repository examples
- Transaction patterns shown
- Migration commands documented

#### Task 8.4: Document Testing Patterns
**File**: `CLAUDE.md`
**Implementation**:
- Document test database setup
- Add async testing examples
- Document fixture usage
**Acceptance Criteria**:
- Test patterns clear
- Async examples work
- Fixture usage explained

## Implementation Notes

1. **Always check existing code** before implementing each task - the project may have evolved
2. **Run tests after each task** to ensure nothing breaks
3. **Commit after each completed task** with descriptive commit messages
4. **Update CLAUDE.md** as you implement new patterns
5. **Check dependencies** are installed before starting each phase

## Testing Strategy Reminders

- Unit tests should be fast and isolated
- Use mocks for external dependencies
- Integration tests can use real database (PostgreSQL in Docker)
- Always test both success and error cases
- Test async behavior explicitly
- Ensure tests are deterministic (no random failures)

## Common Pitfalls to Avoid

1. Don't mix API-specific and shared concerns
2. Don't forget to handle async context properly
3. Don't log sensitive data (passwords, tokens)
4. Don't create circular dependencies between modules
5. Don't forget to test middleware interaction order
6. Don't hardcode configuration values

## Success Criteria for Complete Implementation

- [ ] All exceptions inherit from TributumError
- [ ] All logs include correlation ID when in request context
- [ ] All API responses include security headers
- [ ] Database operations use repository pattern
- [ ] OpenTelemetry traces show full request flow
- [ ] All components have >80% test coverage
- [ ] Documentation is complete and accurate
- [ ] No hardcoded configuration values
- [ ] Clean startup/shutdown with no warnings
- [ ] Integration tests pass with real PostgreSQL
