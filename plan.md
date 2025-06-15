# Cross-Cutting Concerns Implementation Plan

## Revision Notes (Granular Approach)

This plan has been revised to use a more granular task structure that eliminates forward dependencies:
- Tasks that previously assumed future components are now split into basic and enhancement versions
- HTTP-specific features moved to after middleware implementation
- Correlation ID features moved to after context infrastructure
- Each task is now truly self-contained and implementable in sequence

## Context and Important Instructions

This plan was created to implement robust cross-cutting concerns for the Tributum backend project. Key decisions and constraints:

1. **Focus on Cross-Cutting Concerns Only**: This plan specifically addresses infrastructure concerns (error handling, logging, middleware, security headers, request/response logging, database setup with base repository pattern). Domain-specific features are NOT part of this plan.

2. **Technology Stack Decisions**:
   - Database: PostgreSQL with SQLAlchemy 2.0 (async) and Alembic for migrations
   - Observability: OpenTelemetry with GCP integration (Cloud Trace, Cloud Monitoring)
   - Logging: structlog for structured logging with correlation ID support
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
- Phase 1 (Exceptions) → Foundation for all error handling (Tasks 1.1-1.8 complete)
- Phase 2 (Basic Logging) → Basic structlog without correlation IDs (Tasks 2.1-2.5 complete)
- Phase 3 (Context) → Required for correlation IDs (Tasks 3.1-3.4)
- Phase 3.5 (Logging Enhancement) → Add correlation ID support (Tasks 2.2b, 2.3b, 3.5b)
- Phase 4 (API Middleware) → Depends on 1, 2, 3 (Tasks 4.1-4.4)
- Phase 4.5 (Exception Enhancement) → Add HTTP context capture (Tasks 1.6b, 1.7c, 4.5c)
- Phase 5 (OpenTelemetry) → After context setup with error integration (Tasks 5.1-5.5)
- Phase 6 (Database) → Independent but needed before integration (Tasks 6.1-6.11)
- Phase 7 (Integration) → Requires all previous phases
- Phase 8 (Error Aggregators) → Requires enhanced exceptions and middleware (Tasks 8.1-8.5)
- Phase 9 (Final Review) → Documentation consolidation (Task 9.1)

Note: Documentation tasks are embedded throughout phases to keep CLAUDE.md current. The granular approach ensures no forward dependencies.

## Standard Pre-Implementation Checklist for EVERY Task

**MANDATORY**: Before implementing ANY task, you MUST complete these steps IN ORDER:

1. **Read CLAUDE.md Completely**
   - Re-read the ENTIRE Development Guidelines section
   - Pay special attention to:
     - "FUNDAMENTAL PRINCIPLE: Never Bypass Quality Checks"
     - "CRITICAL: Pre-Implementation Analysis Framework"
     - Exception and API patterns sections
     - Any patterns documented for the feature you're implementing

2. **Understand the Current Task**
   - Read the task description carefully
   - Identify all files to be created/modified
   - Review the acceptance criteria
   - Note any dependencies on previous tasks

3. **Analyze Existing Project Code**
   ```bash
   # Search for related patterns
   uv run rg "pattern|keyword" --type py

   # Check for existing similar implementations
   ls -la src/core/ src/api/ src/domain/

   # Read any files mentioned in the task
   # Read related test files
   ```

4. **Verify Configuration**
   - Check `pyproject.toml` for linting/typing rules
   - Review `.pre-commit-config.yaml` for quality checks
   - Ensure you understand what the tools expect

5. **Plan Your Implementation**
   - How will this follow existing patterns?
   - What naming conventions apply?
   - Are there any utilities to reuse?
   - What tests are needed?

**Only proceed with implementation AFTER completing all 5 steps above.**

## Detailed Implementation Plan

### Phase 1: Exception Infrastructure (Foundation)

#### Task 1.1: Create Base Exception Class
**Status**: Complete - Base exception class with error_code and message implemented
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
**Status**: Complete - ErrorCode enum created with standard error codes
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
**Status**: Complete - All specialized exception classes created with appropriate defaults
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
**Status**: Complete - ErrorResponse model created with basic fields
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

#### Task 1.5a: Add Severity and Context to Base Exception
**Status**: Complete - Severity enum and context support added to exceptions
**Pre-Implementation**: Complete the Standard Pre-Implementation Checklist (especially read CLAUDE.md)
**File**: `src/core/exceptions.py`
**Implementation**:
- Add `Severity` enum (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Add `severity` attribute to TributumError (default to ERROR)
- Add `context` dict attribute for capturing business context
- Add method to add context items incrementally
  **Tests**: Update `tests/unit/core/test_exceptions.py`
- Test severity enum values
- Test default severity
- Test context initialization and updates
  **Acceptance Criteria**:
- Severity enum has all levels
- Context is empty dict by default
- Can add context after exception creation

#### Task 1.5b: Add Stack Trace and Exception Chaining
**Status**: Complete - Stack trace capture and exception chaining implemented
**File**: `src/core/exceptions.py`
**Implementation**:
- Add `stack_trace` attribute to capture traceback at creation
- Add `cause` attribute for exception chaining
- Add `fingerprint` for error grouping (based on type + location)
- Implement `__cause__` property for proper exception chaining
  **Tests**: Update `tests/unit/core/test_exceptions.py`
- Test stack trace capture
- Test exception chaining with cause
- Test fingerprint generation
  **Acceptance Criteria**:
- Stack trace captured automatically
- Exception chains properly with Python's exception handling
- Fingerprint is consistent for same error location

#### Task 1.6a: Create Generic Context Utilities
**Status**: Complete - Context utilities created with sensitive data sanitization
**File**: `src/core/error_context.py`
**Implementation**:
- Create `sanitize_context()` to remove sensitive data patterns
- Create `enrich_error()` to add context to TributumError instances
- Define SENSITIVE_FIELD_PATTERNS (password, token, secret, key, etc.)
- Support nested dict sanitization
  **Tests**: `tests/unit/core/test_error_context.py`
- Test sensitive field removal
- Test nested dict sanitization
- Test error enrichment
  **Acceptance Criteria**:
- Common sensitive fields removed
- Nested structures handled
- Original context not modified

#### Task 1.7a: Add Basic Production Fields to Error Response
**Status**: Complete - Timestamp and severity fields added to ErrorResponse
**File**: `src/api/schemas/errors.py`
**Implementation**:
- Add `timestamp` field with timezone (datetime)
- Add `severity` field (str)
- Import datetime and configure proper serialization
  **Tests**: Update `tests/unit/api/schemas/test_errors.py`
- Test timestamp serialization
- Test severity field
- Test JSON output format
  **Acceptance Criteria**:
- Timestamp includes timezone info
- Serializes to ISO format
- Severity field is optional

#### Task 1.7b: Add Service Info to Error Response
**Status**: Complete - ServiceInfo model created and integrated into ErrorResponse
**File**: `src/api/schemas/errors.py`
**Implementation**:
- Create `ServiceInfo` nested model (name, version, environment)
- Add `service_info` field to ErrorResponse
- Make service_info optional
  **Tests**: Update `tests/unit/api/schemas/test_errors.py`
- Test ServiceInfo model
- Test nested model serialization
- Test with and without service info
  **Acceptance Criteria**:
- ServiceInfo validates fields
- Properly nested in JSON output
- Optional field handling correct

#### Task 1.8: Document Enhanced Exception Features
**Status**: Complete - Added concise documentation for all enhanced exception features
**File**: `CLAUDE.md`
**Implementation**:
- Document severity levels and their usage
- Add examples of using context with exceptions
- Document stack trace capture behavior
- Add examples of exception chaining
- Document the enhanced ErrorResponse fields
  **Acceptance Criteria**:
- Clear examples for each new feature
- Guidelines on when to use each severity level
- Context usage best practices documented

### Phase 2: Logging Infrastructure (with structlog)

#### Task 2.1: Add structlog Dependencies and Configuration
**Status**: Complete - structlog dependency added, LogConfig created with environment-based defaults
**File**: `pyproject.toml` and `src/core/config.py`
**Implementation**:
- Add structlog dependency to pyproject.toml
- Add `LogConfig` nested class in Settings
- Add fields: log_level, log_format (json/console), render_json_logs
- Add structlog-specific settings (add_timestamp, timestamper format)
**Tests**: Update `tests/unit/core/test_config.py`
- Test default values
- Test environment override
**Acceptance Criteria**:
- structlog installed with correct version
- Configuration supports both development and production modes

#### Task 2.2a: Create Basic structlog Setup
**Status**: Complete - Basic structlog configuration with dev/prod pipelines
**File**: `src/core/logging.py`
**Implementation**:
- Create `configure_structlog()` function with basic processors
- Add processors: add_log_level, add_timestamp, add_logger_name
- Add CallsiteParameterAdder for file/function/line info
- Configure different pipelines for dev (console) vs prod (JSON)
- Integrate with stdlib logging for third-party libraries
**Tests**: `tests/unit/core/test_logging.py`
- Test JSON output structure
- Test console output format
- Test processor pipeline
**Acceptance Criteria**:
- Outputs structured logs in configured format
- Basic processors work correctly
- Console vs JSON format switching works

#### Task 2.3a: Create Basic Logger Factory
**Status**: Complete - Logger factory and context manager implemented
**File**: `src/core/logging.py`
**Implementation**:
- Create `get_logger(name)` function returning bound structlog logger
- Create `log_context()` context manager for temporary bindings
- Support lazy evaluation of expensive log data
- Basic context binding without contextvars
**Tests**: Update `tests/unit/core/test_logging.py`
- Test logger creation
- Test temporary context bindings
- Test lazy evaluation
**Acceptance Criteria**:
- Logger factory creates named loggers
- Temporary bindings work in context manager
- Lazy evaluation improves performance

#### Task 2.4: Create Exception Logging Utilities
**Status**: Complete - log_exception() helper created with severity-based logging
**File**: `src/core/logging.py`
**Implementation**:
- Create `log_exception()` helper with full context
- Add exception processor to capture stack traces
- Add error fingerprinting for log aggregation
- Support exception chain logging
**Tests**: Update `tests/unit/core/test_logging.py`
- Test exception logging with context
- Test stack trace formatting
- Test exception chain handling
**Acceptance Criteria**:
- Exceptions logged with full stack trace
- Context from TributumError included
- Exception chains preserved

#### Task 2.5: Document Basic Logging Setup
**Status**: Complete - Concise logging documentation added to CLAUDE.md
**File**: `CLAUDE.md`
**Implementation**:
- Document structlog configuration approach
- Add examples of basic logger usage
- Document log levels and when to use them
- Add guidelines for structured logging fields
- Document exception logging patterns
**Acceptance Criteria**:
- Clear examples of logger usage
- Best practices for structured data
- Performance considerations noted

### Phase 3: Request Context Infrastructure

#### Task 3.1: Create Correlation ID Generator
**Status**: Complete - UUID4-based correlation ID generator implemented
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
**Status**: Complete - RequestContext class implemented with contextvars
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
**Status**: Complete - RequestContextMiddleware implemented with full test coverage
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

#### Task 3.4: Document Context Infrastructure
**Status**: Complete - Succinct documentation added to CLAUDE.md
**File**: `CLAUDE.md`
**Implementation**:
- Document correlation ID pattern and usage
- Add examples of context propagation
- Document RequestContext usage
- Add middleware integration examples
**Acceptance Criteria**:
- Clear explanation of correlation ID flow
- Examples show async context propagation
- Best practices for context usage

### Phase 3.5: Logging Enhancement (After Context Infrastructure)

#### Task 2.2b: Add Correlation ID Support to structlog
**Status**: Complete - Correlation ID processor added to structlog pipeline
**File**: `src/core/logging.py`
**Implementation**:
- Add `bind_contextvars` processor to structlog configuration
- Update processor pipeline to include correlation ID from context
- Ensure correlation ID appears in all log entries when available
**Tests**: Update `tests/unit/core/test_logging.py`
- Test correlation ID inclusion in logs
- Test logs without correlation ID
- Test context isolation
**Acceptance Criteria**:
- Correlation ID automatically included when set
- No errors when correlation ID missing
- Context properly isolated between requests

#### Task 2.3b: Enhance Logger Factory with Contextvars
**Status**: Pending
**File**: `src/core/logging.py`
**Implementation**:
- Update `get_logger()` to use contextvars for automatic context binding
- Ensure correlation ID propagates through async calls
- Add helper to bind additional request context
**Tests**: Update `tests/unit/core/test_logging.py`
- Test async context propagation
- Test multiple concurrent contexts
- Test context cleanup
**Acceptance Criteria**:
- Context propagates through async boundaries
- Multiple requests maintain separate contexts
- No context leakage between requests

#### Task 3.5b: Document Enhanced Logging
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Update logging documentation with correlation ID integration
- Add examples of logs with correlation IDs
- Document async context propagation in logging
- Show how to trace requests across log entries
**Acceptance Criteria**:
- Examples show correlation ID in logs
- Async logging patterns documented
- Request tracing explained

### Phase 4: API Middleware

#### Task 4.1: Create Security Headers Middleware
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
**File**: `src/api/middleware/error_handler.py`
**Implementation**:
- Create exception handler for `TributumError` with full context capture
- Extract stack trace, error context, and severity from enhanced exceptions
- Create handler for `RequestValidationError` with field-level details
- Create handler for generic `Exception` with safe error messages
- Include correlation ID, timestamp, and service info in all responses
- Log exceptions with full context using structlog
- Sanitize error details before sending to client
- Different response detail levels for dev vs production
**Tests**: `tests/integration/api/test_error_handling.py`
- Test each exception type handling
- Test error response format with all new fields
- Test correlation ID inclusion
- Test debug info only shown in development
- Test sensitive data sanitization
- Test stack trace capture and logging
**Acceptance Criteria**:
- Returns correct HTTP status codes based on error type
- Error format matches enhanced ErrorResponse model
- Stack traces logged but not exposed to clients in production
- Debug information only available in development
- All errors logged with full context for monitoring

#### Task 4.4: Document Middleware Patterns
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Document middleware ordering and why it matters
- Add security headers best practices
- Document request logging patterns
- Add error handling middleware examples
- Show complete middleware integration
**Acceptance Criteria**:
- Middleware order clearly explained
- Security implications documented
- Error handling patterns shown

### Phase 4.5: Exception Enhancement (After Middleware)

#### Task 1.6b: Add HTTP Context Capture
**Status**: Pending
**File**: `src/core/error_context.py`
**Implementation**:
- Create `capture_request_context()` to extract HTTP request info
- Extract method, path, headers, query params from FastAPI Request
- Filter out sensitive headers (Authorization, Cookie, etc.)
- Support for custom context providers
**Tests**: Update `tests/unit/core/test_error_context.py`
- Test request context extraction
- Test sensitive header filtering
- Test with missing request object
**Acceptance Criteria**:
- Captures all relevant HTTP info
- Sensitive headers removed
- Handles missing request gracefully

#### Task 1.7c: Add Debug Info and Request ID to Error Response
**Status**: Pending
**File**: `src/api/schemas/errors.py`
**Implementation**:
- Add `debug_info` optional field for development environments
- Add `request_id` field (separate from correlation_id)
- Debug info should include stack trace and error context
**Tests**: Update `tests/unit/api/schemas/test_errors.py`
- Test debug_info structure
- Test conditional debug info based on environment
- Test request_id field
**Acceptance Criteria**:
- Debug info only populated in development
- Request ID is separate from correlation ID
- Stack trace properly formatted in debug info

#### Task 4.5c: Document Complete Error Handling
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Document complete error handling flow with HTTP context
- Add examples of errors with full context capture
- Document debug info usage in development
- Show error aggregation patterns
- Add production vs development error responses
**Acceptance Criteria**:
- Complete error flow documented
- HTTP context capture explained
- Debug mode usage clear

### Phase 5: OpenTelemetry Setup

#### Task 5.1: Add OpenTelemetry Dependencies
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
**File**: `src/core/observability.py`
**Implementation**:
- Create `setup_tracing()` function
- Configure GCP trace exporter
- Set up trace provider with sampling
- Create `get_tracer()` function
- Add custom span processor for error tracking
- Integrate with TributumError context capture
- Add error severity to span attributes
**Tests**: `tests/unit/core/test_observability.py`
- Test setup with tracing disabled
- Test tracer creation
- Test error context in spans
- Test span attributes for errors
**Acceptance Criteria**:
- Tracing can be disabled
- Returns configured tracer
- No errors when GCP not available
- Errors include full context in spans
- Severity properly mapped to span status

#### Task 5.4: Instrument FastAPI
**Status**: Pending
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

#### Task 5.5: Document Observability Setup
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Document OpenTelemetry integration
- Add tracing examples
- Document span attributes and error tracking
- Show GCP integration setup
- Add performance monitoring guidelines
**Acceptance Criteria**:
- Tracing setup clearly explained
- Error tracking in spans documented
- GCP integration steps included

### Phase 6: Database Infrastructure

#### Task 6.1: Add Database Dependencies
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
**Implementation**:
- Create empty initial migration
- Test upgrade/downgrade
**Tests**: Manual verification
**Acceptance Criteria**:
- Migration runs without errors
- Can upgrade and downgrade

#### Task 6.11: Document Database Patterns
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Document repository pattern implementation
- Add async database examples
- Document transaction patterns
- Add migration workflow and commands
- Show testing strategies with async DB
**Acceptance Criteria**:
- Repository pattern clearly explained
- Async patterns documented
- Migration workflow complete

### Phase 7: Integration

#### Task 7.1: Wire Middleware in Correct Order
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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
**Status**: Pending
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

### Phase 8: Error Aggregator Integration

#### Task 8.1: Add Sentry SDK Dependencies
**Status**: Pending
**File**: `pyproject.toml` and `src/core/config.py`
**Implementation**:
- Add sentry-sdk[fastapi] dependency
- Add `ErrorAggregatorConfig` to Settings
- Add fields: sentry_dsn (optional), environment, release, sample_rate
- Support disabling in development/testing
**Tests**: Update `tests/unit/core/test_config.py`
- Test configuration loading
- Test DSN validation
**Acceptance Criteria**:
- Sentry SDK installed
- Configuration supports enable/disable
- DSN only required when enabled

#### Task 8.2: Create Sentry Integration
**Status**: Pending
**File**: `src/core/error_aggregator.py`
**Implementation**:
- Create `setup_sentry()` function
- Configure Sentry with enhanced error context
- Add custom before_send hook to include TributumError context
- Integrate with structlog for breadcrumbs
- Map severity levels appropriately
- Filter sensitive data from context
**Tests**: `tests/unit/core/test_error_aggregator.py`
- Test setup with Sentry disabled
- Test context enrichment
- Test sensitive data filtering
**Acceptance Criteria**:
- Sentry can be disabled
- TributumError context included in reports
- Stack traces properly captured
- Sensitive data filtered

#### Task 8.3: Create GCP Error Reporting Integration
**Status**: Pending
**File**: `src/core/error_aggregator.py`
**Implementation**:
- Add GCP Error Reporting client setup
- Create `report_error_to_gcp()` function
- Map TributumError to GCP error format
- Include service context and labels
- Support both Sentry and GCP simultaneously
**Tests**: Update `tests/unit/core/test_error_aggregator.py`
- Test GCP client setup
- Test error format mapping
- Test with GCP disabled
**Acceptance Criteria**:
- GCP Error Reporting can be disabled
- Errors include proper service context
- Works alongside Sentry

#### Task 8.4: Integrate Error Aggregators with Middleware
**Status**: Pending
**File**: `src/api/middleware/error_handler.py`
**Implementation**:
- Call error aggregator reporting in exception handlers
- Ensure errors are reported before response is sent
- Add request context to error reports
- Handle aggregator failures gracefully
**Tests**: `tests/integration/api/test_error_aggregator_integration.py`
- Test error reporting flow
- Test aggregator failure handling
- Test context inclusion
**Acceptance Criteria**:
- All unhandled errors reported
- TributumError context preserved
- Aggregator failures don't break response

#### Task 8.5: Document Error Aggregator Integration
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Document Sentry and GCP Error Reporting setup
- Add configuration examples
- Document error filtering and sanitization
- Show how errors flow to aggregators
- Add monitoring best practices
**Acceptance Criteria**:
- Both Sentry and GCP setup documented
- Configuration clearly explained
- Error flow diagram or explanation

### Phase 9: Final Documentation Review

#### Task 9.1: Review and Consolidate Documentation
**Status**: Pending
**File**: `CLAUDE.md`
**Implementation**:
- Review all documentation added throughout phases
- Ensure consistency and completeness
- Add any missing cross-references
- Create a quick reference section
- Verify all examples work with current code
**Acceptance Criteria**:
- Documentation is cohesive
- No contradictions or outdated info
- Quick reference helps developers

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

- [x] All exceptions inherit from TributumError with enhanced context
- [x] Exception stack traces captured and logged but not exposed to clients
- [ ] All logs use structlog with correlation ID when in request context
- [x] Error responses include timestamp, severity, and service info
- [ ] Debug information only available in development environment
- [ ] All API responses include security headers
- [ ] Database operations use repository pattern
- [ ] OpenTelemetry traces show full request flow with error context
- [ ] Sentry/GCP Error Reporting integration captures all unhandled errors
- [x] Sensitive data properly sanitized in logs and error reports
- [ ] All components have >80% test coverage
- [ ] Documentation is complete and accurate
- [ ] No hardcoded configuration values
- [ ] Clean startup/shutdown with no warnings
- [ ] Integration tests pass with real PostgreSQL
- [ ] Error aggregators properly configured for production use
