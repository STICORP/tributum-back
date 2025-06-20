# Cross-Cutting Concerns Implementation Plan

## Current Status Summary

**Completed Phases:**
- ✅ Phase 1: Exception Infrastructure (Tasks 1.1-1.8)
- ✅ Phase 2: Logging Infrastructure (Tasks 2.1-2.5)
- ✅ Phase 3: Request Context Infrastructure (Tasks 3.1-3.4)
- ✅ Phase 3.5: Logging Enhancement (Tasks 2.2b, 2.3b, 3.5b)
- ✅ Phase 3.6: JSON Performance Optimization (Tasks 3.6.1-3.6.7)
- ✅ Phase 4: API Middleware (Tasks 4.1-4.4, including 4.2b)
- ✅ Phase 4.5: Exception Enhancement (Tasks 1.6b, 1.7c, 4.5c)

**Pending Phases:**
- ✅ Phase 5: OpenTelemetry Setup (Tasks 5.1-5.5)
- ⏳ Phase 6: Database Infrastructure (Task 6.1 complete, Tasks 6.2-6.11 pending)
- ⏳ Phase 6.2a: Minimal Docker Infrastructure (Tasks 6.2a.1-6.2a.5) - NEW
- ⏳ Phase 6.12: Full Docker Development Environment (Tasks 6.12.1-6.12.4) - NEW
- ⏳ Phase 7: Integration (Tasks 7.1-7.4)
- ⏳ Phase 8: Error Aggregator Integration (Tasks 8.1-8.5)
- ⏳ Phase 9: Final Documentation Review (Task 9.1)

**Next Task:** Task 6.2 - Create Database Configuration

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
   - Containerization: Docker with Docker Compose for local development and testing
   - Container Registry: GCP Artifact Registry (for production deployment)

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
- Phase 3 (Context) → Required for correlation IDs (Tasks 3.1-3.4 complete)
- Phase 3.5 (Logging Enhancement) → Add correlation ID support (Tasks 2.2b, 2.3b, 3.5b complete)
- Phase 3.6 (JSON Performance) → Optimize JSON serialization for logs and API (Tasks 3.6.1-3.6.7 complete)
- Phase 4 (API Middleware) → Depends on 1, 2, 3, 3.6 (Tasks 4.1-4.4, including 4.2b complete)
- Phase 4.5 (Exception Enhancement) → Add HTTP context capture (Tasks 1.6b, 1.7c, 4.5c complete)
- Phase 5 (OpenTelemetry) → After context setup with error integration (Tasks 5.1-5.5)
- Phase 6 (Database) → Independent but needed before integration (Tasks 6.1-6.11)
- Phase 6.2a (Minimal Docker) → After Task 6.2, provides PostgreSQL for testing (Tasks 6.2a.1-6.2a.5)
- Phase 6.12 (Full Docker) → After database infrastructure complete (Tasks 6.12.1-6.12.4)
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
**Status**: Complete - Logger factory enhanced with contextvars support
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
**Status**: Complete - Documentation updated with async context propagation
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

### Phase 3.6: JSON Performance Optimization (After Context Infrastructure)

#### Task 3.6.1: Add orjson Dependency
**Status**: Complete - orjson v3.10.18 added to dependencies
**Pre-Implementation**: Check latest orjson version compatible with Python 3.13
**File**: `pyproject.toml`
**Implementation**:
- Add orjson dependency to pyproject.toml
- Check version: `curl -s https://pypi.org/pypi/orjson/json | grep -o '"version":"[^"]*"' | head -1`
- Ensure compatibility with Python 3.13
**Tests**: Run `uv sync` and verify installation
**Acceptance Criteria**:
- orjson installs without conflicts
- Compatible with Python 3.13 and existing dependencies

#### Task 3.6.2: Create Custom orjson Processor for structlog
**Status**: Complete - ORJSONRenderer implemented with full type handling
**File**: `src/core/logging.py`
**Implementation**:
- Create `ORJSONRenderer` class that implements structlog processor interface
- Handle all Python types currently used in logs (datetime, UUID, exceptions)
- Use orjson.dumps with appropriate options (OPT_SORT_KEYS for consistency)
- Ensure compatibility with existing log processors
**Tests**: Update `tests/unit/core/test_logging.py`
- Test JSON output structure remains the same
- Test performance improvement over standard JSONRenderer
- Test special type handling (datetime with timezone, UUID, exceptions)
- Test with all log levels and contexts
**Acceptance Criteria**:
- Logs maintain exact same structure as before
- Performance improvement measurable
- All existing log types handled correctly
- No loss of information in logs

#### Task 3.6.3: Update Logging Configuration to Use orjson
**Status**: Complete - orjson renderer integrated with fallback to standard JSONRenderer
**File**: `src/core/logging.py`
**Implementation**:
- Replace `structlog.processors.JSONRenderer()` with `ORJSONRenderer()` in prod_processors
- Ensure fallback to standard JSONRenderer if orjson import fails
- Maintain existing processor pipeline order
**Tests**: Update `tests/unit/core/test_logging.py`
- Test configuration with orjson renderer
- Test fallback behavior if orjson unavailable
- Verify correlation ID and context still work
**Acceptance Criteria**:
- JSON logs use orjson in production mode
- Console logs unchanged in development mode
- Graceful fallback if orjson unavailable

#### Task 3.6.4: Create ORJSONResponse Class
**Status**: Complete - ORJSONResponse implemented with full test coverage
**File**: `src/api/utils/responses.py`
**Implementation**:
- Create `ORJSONResponse` class extending FastAPI's Response
- Implement render method using orjson.dumps
- Set media_type to "application/json"
- Handle orjson options (OPT_INDENT_2 for readability in debug mode)
- Support Pydantic model serialization via model_dump()
**Tests**: `tests/unit/api/utils/test_responses.py`
- Test basic type serialization
- Test Pydantic model serialization
- Test datetime with timezone (crucial for ErrorResponse.timestamp)
- Test None values and empty responses
- Compare performance with JSONResponse
**Acceptance Criteria**:
- Correctly serializes all API response types
- Handles ErrorResponse model with timestamp
- Maintains compatibility with FastAPI
- Measurable performance improvement

#### Task 3.6.5: Configure FastAPI to Use ORJSONResponse
**Status**: Complete - FastAPI configured to use ORJSONResponse as default
**File**: `src/api/main.py`
**Implementation**:
- Import ORJSONResponse from utils.responses
- Add `default_response_class=ORJSONResponse` to FastAPI constructor
- Ensure all existing endpoints work without modification
- Verify OpenAPI schema generation still functions
**Tests**: `tests/integration/api/test_orjson_integration.py`
- Test all existing endpoints return valid JSON
- Test error responses serialize correctly
- Test OpenAPI endpoints (/docs, /redoc, /openapi.json)
- Test response headers include correct content-type
**Acceptance Criteria**:
- All endpoints use orjson automatically
- No changes required to endpoint code
- OpenAPI documentation accessible
- Error responses maintain structure

#### Task 3.6.6: Verify orjson Compatibility with Existing Components
**Status**: Complete - All tests pass, no regressions found
**Implementation**:
- Run all existing tests to ensure no regressions
- Check ErrorResponse serialization with timestamp
- Verify correlation ID in logs still works
- Test with different log levels and contexts
**Tests**: Run full test suite
**Acceptance Criteria**:
- All existing tests pass
- No functionality degradation
- Performance improvement confirmed

#### Task 3.6.7: Document orjson Integration
**Status**: Complete - Documentation added to CLAUDE.md
**File**: `CLAUDE.md`
**Implementation**:
- Add section on JSON performance optimization
- Document why orjson was chosen (performance, memory efficiency)
- Note any limitations or special handling
- Add example of custom serialization if needed
- Update performance considerations
**Acceptance Criteria**:
- Clear explanation of orjson benefits
- Any gotchas documented
- Examples if custom serialization needed

### Phase 4: API Middleware

#### Task 4.1: Create Security Headers Middleware
**Status**: Complete - SecurityHeadersMiddleware implemented with configurable HSTS support
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
**Status**: Complete
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

#### Task 4.2b: Add Request/Response Body Logging
**Status**: Complete - Full request/response body logging with sanitization implemented
**Pre-requisites**: Task 4.2 (RequestLoggingMiddleware exists)
**File**: `src/api/middleware/request_logging.py`
**Implementation**:
- Implement `log_request_body` functionality in existing middleware
- Implement `log_response_body` functionality
- Read request body safely (handle streaming, preserve for downstream)
- Support JSON content type with full parsing and sanitization
- Support form data content type with sanitization
- Handle multipart/binary data (log metadata only, not content)
- Add configurable size limits (default 10KB for logs)
- Truncate large bodies with clear indication
- Use `sanitize_context` on parsed request/response bodies
- Add request headers logging (sanitized, exclude Authorization, Cookie)
- Add response headers logging if enabled
- Handle request body read errors gracefully
**Tests**: Update `tests/unit/api/middleware/test_request_logging.py`
- Test JSON request body logging with sanitization
- Test form data request body logging with sanitization
- Test large body truncation
- Test binary/multipart data handling (metadata only)
- Test request body read errors don't break request
- Test response body logging when enabled
- Test headers logging with sensitive header filtering
- Test that request body is still available to endpoints
- Test with various content types
**Acceptance Criteria**:
- Request bodies are logged when `log_request_body=True`
- Response bodies are logged when `log_response_body=True`
- All sensitive data is sanitized using existing patterns
- Large bodies are truncated with size indication
- Binary data shows metadata only (content-type, size)
- Request processing continues even if body logging fails
- Original request body remains accessible to endpoints
- Performance impact is minimal
- Memory usage is bounded by size limits

#### Task 4.3: Create Global Exception Handler
**Status**: Complete - All exception handlers implemented with proper logging and standardized responses
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
**Status**: Complete - Middleware patterns documented in CLAUDE.md
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
**Status**: Complete - HTTP request context capture implemented with security filtering
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
**Status**: Complete - Debug info and request ID fields added to ErrorResponse
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
**Status**: Complete - Added concise error context and debug info documentation
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
**Status**: Complete - All OpenTelemetry packages added with latest versions
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
**Status**: Complete - ObservabilityConfig added with all required fields and tests
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
**Status**: Complete
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
**Status**: Complete
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
**Status**: Complete
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
**Status**: Complete - All database dependencies added with latest versions
**File**: `pyproject.toml`
**Implementation**:
- Added sqlalchemy[asyncio]>=2.0.41 (latest stable version)
- Added asyncpg>=0.30.0 (PostgreSQL async driver)
- Added alembic>=1.16.2 (latest version)
- Added greenlet>=3.2.3 (for async SQLAlchemy)
**Tests**: `uv sync` ran successfully
**Acceptance Criteria**:
- All packages installed successfully
- Versions are compatible with Python 3.13
- SQLAlchemy async components import correctly

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

### Phase 6.2a: Minimal Docker Infrastructure

This phase provides the minimal Docker setup needed to enable database testing for subsequent tasks. It focuses only on what's required for tests to pass, with the full development environment coming later in Phase 6.12.

#### Task 6.2a.1: Create Docker Directory Structure
**Status**: Pending
**Pre-requisites**: Task 6.2 complete
**Files**:
- `docker/postgres/init.sql`
- `.dockerignore`
- `.env.example` (database variables only)
**Implementation**:
- Create `docker/` directory with subdirectories: `postgres/`, `scripts/`
- Create `docker/postgres/init.sql` with test database creation:
  ```sql
  -- Create test database
  CREATE DATABASE tributum_test WITH TEMPLATE tributum_db;
  GRANT ALL PRIVILEGES ON DATABASE tributum_test TO tributum;
  ```
- Create `.dockerignore` with minimal exclusions (reuse .gitignore patterns)
- Create `.env.example` with only database-related variables
**Tests**:
- Verify directory structure exists
- Validate SQL syntax
- Ensure .env.example has all required DB variables
**Acceptance Criteria**:
- Directory structure follows Docker best practices
- init.sql creates test database successfully
- .env.example documents all database configuration

#### Task 6.2a.2: Create PostgreSQL Docker Compose
**Status**: Pending
**Pre-requisites**: Task 6.2a.1
**File**: `docker-compose.test.yml`
**Implementation**:
- Create minimal docker-compose for testing only:
  ```yaml
  version: '3.8'
  services:
    postgres:
      image: postgres:17-alpine
      environment:
        POSTGRES_USER: tributum
        POSTGRES_PASSWORD: tributum_pass
        POSTGRES_DB: tributum_db
      volumes:
        - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
      ports:
        - "5432:5432"
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U tributum -d tributum_db"]
        interval: 2s
        timeout: 5s
        retries: 15
  ```
**Tests**:
- Run `docker-compose -f docker-compose.test.yml up -d`
- Verify PostgreSQL starts and becomes healthy
- Connect with psql to verify both databases exist
**Acceptance Criteria**:
- PostgreSQL 17 starts successfully
- Health check passes within 30 seconds
- Both tributum_db and tributum_test databases exist
- Can connect from host machine

#### Task 6.2a.3: Create Test Database Setup
**Status**: Pending
**Pre-requisites**: Task 6.2a.2
**Files**:
- `docker/scripts/wait-for-postgres.sh`
- Update `pyproject.toml` (pytest_env section)
**Implementation**:
- Create wait-for-postgres.sh script:
  ```bash
  #!/bin/bash
  until pg_isready -h ${DATABASE_HOST:-localhost} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USER:-tributum}
  do
    echo "Waiting for PostgreSQL..."
    sleep 2
  done
  ```
- Update pyproject.toml pytest_env to include:
  ```toml
  DATABASE_URL = "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_test"
  TEST_DATABASE_URL = "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_test"
  ```
- Make script executable
**Tests**:
- Run script with PostgreSQL down and up
- Verify existing tests still pass
- Check environment variables are set in tests
**Acceptance Criteria**:
- Wait script detects PostgreSQL availability
- Test environment has database URL configured
- No regression in existing tests
- Script handles both local and CI environments

#### Task 6.2a.4: Update GitHub Actions for Docker
**Status**: Pending
**Pre-requisites**: Task 6.2a.3
**File**: `.github/workflows/checks.yml`
**Implementation**:
- Add PostgreSQL service to test job:
  ```yaml
  services:
    postgres:
      image: postgres:17-alpine
      env:
        POSTGRES_USER: tributum
        POSTGRES_PASSWORD: tributum_pass
        POSTGRES_DB: tributum_db
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
      ports:
        - 5432:5432
  ```
- Add environment variables for database URL
- Update test commands to use database
**Tests**:
- Push to branch and verify CI workflow runs
- Check PostgreSQL service starts in CI
- Ensure all existing tests still pass
**Acceptance Criteria**:
- CI workflow starts PostgreSQL service
- Database is accessible in test environment
- All existing tests continue to pass
- No increase in CI runtime for non-DB tests

#### Task 6.2a.5: Create Database Test Fixtures
**Status**: Pending
**Pre-requisites**: Task 6.2a.4
**Files**:
- `tests/fixtures/database.py`
- Update `tests/conftest.py`
**Implementation**:
- Create database fixture module:
  ```python
  @pytest.fixture
  def database_url(monkeypatch):
      """Provide test database URL."""
      url = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
      if not url:
          pytest.skip("No database URL configured")
      return url

  @pytest.fixture
  async def db_connection(database_url):
      """Provide raw database connection for testing."""
      # Placeholder - will be implemented with actual connection in Task 6.4
      pass
  ```
- Import fixtures in conftest.py
- Add fixture for verifying database connectivity
**Tests**:
- Create test that uses database_url fixture
- Verify fixture skips when no database configured
- Test fixture provides correct URL
**Acceptance Criteria**:
- Fixtures are available in all tests
- Tests skip gracefully without database
- Database URL is correctly configured
- Ready for actual database implementation

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

### Phase 6.12: Full Docker Development Environment

This phase builds upon the minimal Docker infrastructure to provide a complete development environment with hot-reload, debugging capabilities, and production-like setup.

#### Task 6.12.1: Create Application Dockerfile
**Status**: Pending
**Pre-requisites**: Phase 6 complete (Tasks 6.1-6.11)
**Files**:
- `docker/app/Dockerfile`
- `docker/app/Dockerfile.dev`
- `docker/scripts/entrypoint.sh`
**Implementation**:
- Create multi-stage production Dockerfile:
  ```dockerfile
  # Build stage
  FROM python:3.13-slim as builder
  RUN pip install --no-cache-dir uv
  WORKDIR /build
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-dev

  # Runtime stage
  FROM python:3.13-slim
  RUN useradd -m -u 1000 tributum
  WORKDIR /app
  COPY --from=builder /build/.venv /app/.venv
  COPY . .
  USER tributum
  ENV PATH="/app/.venv/bin:$PATH"
  ENTRYPOINT ["/app/docker/scripts/entrypoint.sh"]
  ```
- Create development Dockerfile with hot-reload support
- Create entrypoint script for migrations and startup
**Tests**:
- Build both Docker images successfully
- Verify non-root user in production image
- Test entrypoint script execution
**Acceptance Criteria**:
- Production image is minimal and secure
- Development image supports hot-reload
- Entrypoint handles migrations gracefully
- Images build without errors

#### Task 6.12.2: Create Development Docker Compose
**Status**: Pending
**Pre-requisites**: Task 6.12.1
**Files**:
- `docker-compose.yml`
- `docker-compose.dev.yml`
- Update `.env.example` with all variables
**Implementation**:
- Create base docker-compose.yml:
  ```yaml
  version: '3.8'
  services:
    api:
      build:
        context: .
        dockerfile: docker/app/Dockerfile
      environment:
        - DATABASE_URL=postgresql+asyncpg://tributum:tributum_pass@postgres:5432/tributum_db
      depends_on:
        postgres:
          condition: service_healthy
      ports:
        - "8000:8000"

    postgres:
      image: postgres:17-alpine
      # ... (reuse configuration from test compose)
  ```
- Create docker-compose.dev.yml with overrides:
  ```yaml
  services:
    api:
      build:
        dockerfile: docker/app/Dockerfile.dev
      volumes:
        - ./src:/app/src
        - ./tests:/app/tests
      command: uvicorn src.api.main:app --reload --host 0.0.0.0
  ```
- Update .env.example with ALL environment variables from analysis
**Tests**:
- Run full stack with docker-compose up
- Verify hot-reload works with code changes
- Test database connectivity from API
**Acceptance Criteria**:
- All services start successfully
- Hot-reload works in development
- Services communicate properly
- Environment variables documented

#### Task 6.12.3: Add Docker Makefile Commands
**Status**: Pending
**Pre-requisites**: Task 6.12.2
**File**: `Makefile`
**Implementation**:
- Add Docker commands section to Makefile:
  ```makefile
  # Docker commands
  docker-build:  ## Build all Docker images
  	docker-compose build

  docker-up:  ## Start all services
  	docker-compose up -d

  docker-up-dev:  ## Start development environment
  	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

  docker-down:  ## Stop all services
  	docker-compose down

  docker-clean:  ## Clean all Docker resources
  	docker-compose down -v --remove-orphans

  docker-logs:  ## View logs (use SERVICE=api for specific service)
  	docker-compose logs -f $${SERVICE:-}

  docker-shell:  ## Shell into API container
  	docker-compose exec api /bin/bash

  docker-psql:  ## Connect to PostgreSQL
  	docker-compose exec postgres psql -U tributum -d tributum_db

  docker-test:  ## Run tests in Docker
  	docker-compose -f docker-compose.test.yml run --rm api pytest

  docker-migrate:  ## Run database migrations
  	docker-compose exec api alembic upgrade head
  ```
- Ensure commands follow existing Makefile style
- Add help documentation for each command
**Tests**:
- Test each command works correctly
- Verify help output includes Docker commands
- Ensure no conflicts with existing commands
**Acceptance Criteria**:
- All commands work as documented
- Consistent with existing Makefile patterns
- Help text is clear and accurate
- No breaking changes to existing commands

#### Task 6.12.4: Document Docker Workflow
**Status**: Pending
**Pre-requisites**: Task 6.12.3
**File**: `CLAUDE.md`
**Implementation**:
- Add Docker Development section covering:
  - Quick start guide for new developers
  - Environment variable configuration
  - Common Docker commands via Make
  - Debugging in containers
  - Database management in Docker
  - Troubleshooting guide
- Add Docker deployment considerations:
  - Production image optimization
  - Security best practices
  - GCP deployment notes
- Update existing sections to mention Docker alternatives
**Tests**:
- Follow documentation to set up from scratch
- Verify all commands work as documented
- Test troubleshooting steps
**Acceptance Criteria**:
- Complete Docker setup guide
- All variables documented with examples
- Common issues and solutions covered
- Integration with existing workflow clear

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
6. **Prioritize observability** - Log all relevant request/response data with proper sanitization

## Testing Strategy Reminders

- Unit tests should be fast and isolated
- Use mocks for external dependencies
- Integration tests use real PostgreSQL via docker-compose.test.yml
- Database tests use fixtures from Phase 6.2a
- Always test both success and error cases
- Test async behavior explicitly
- Ensure tests are deterministic (no random failures)
- CI runs tests with PostgreSQL service container

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
- [x] All logs use structlog with correlation ID when in request context
- [x] Error responses include timestamp, severity, and service info
- [x] High-performance JSON serialization with orjson for logs and API responses
- [x] Debug information only available in development environment (completed in Task 4.3)
- [x] All API responses include security headers (completed in Task 4.1)
- [x] Request/response bodies are logged with proper sanitization (completed in Task 4.2b)
- [ ] Database operations use repository pattern
- [ ] OpenTelemetry traces show full request flow with error context
- [ ] Sentry/GCP Error Reporting integration captures all unhandled errors
- [x] Sensitive data properly sanitized in logs and error reports
- [ ] All components have >80% test coverage
- [x] Documentation is complete and accurate (for implemented features)
- [ ] No hardcoded configuration values
- [ ] Clean startup/shutdown with no warnings
- [ ] Integration tests pass with real PostgreSQL
- [ ] Error aggregators properly configured for production use
- [ ] Docker development environment fully functional
- [ ] CI/CD pipeline runs tests with containerized PostgreSQL
- [ ] All environment variables documented in .env.example
- [ ] Production Docker image is optimized and secure
