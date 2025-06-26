# Task 2: Performance Monitoring

## Overview
Enhance the existing performance monitoring capabilities by building on the current request logging middleware, adding database query tracking, and integrating with OpenTelemetry for comprehensive observability.

## Project Context

### Current Performance Monitoring
The project already has performance monitoring infrastructure:

1. **Request Logging** (`src/api/middleware/request_logging.py`):
   - Tracks request duration in milliseconds (line 386)
   - Logs request start/completion with correlation IDs
   - Captures request method, path, status code
   - Has configurable body logging (not yet in central config)

2. **OpenTelemetry Integration** (`src/core/observability.py`):
   - Tracing setup with GCP Cloud Trace exporter
   - FastAPI instrumentation via `FastAPIInstrumentor`
   - SQLAlchemy instrumentation ready to be enabled
   - Span creation for health checks and startup

3. **Database Infrastructure** (`src/infrastructure/database/session.py`):
   - Async SQLAlchemy engine with performance settings
   - Connection pooling configured
   - No query logging or event listeners currently

4. **Type System** (`src/core/types.py`):
   - Contains type aliases like `JSONDict`, `ErrorContext`
   - Ready for additional performance-related types

### Architecture Patterns to Follow
- Enhance existing components rather than creating new ones
- Use OpenTelemetry for metrics and tracing
- Leverage correlation IDs throughout
- Follow async patterns (no blocking operations)
- Integrate with GCP services (Cloud Trace, Cloud Monitoring)

## Tasks

### Task 2.1: Enhanced Request Performance Metrics
**Status**: ✅ completed
**Files to modify**:
- `src/api/middleware/request_logging.py`
- `src/core/config.py` (add performance thresholds)
- `src/core/types.py` (add PerformanceThresholds type alias)

**Current State**:
- Middleware already tracks `duration_ms` (line 386)
- Has infrastructure for body size tracking via `_capture_response_body()`
- Uses `time.time()` for basic timing

**Functional Requirements**:
1. Enhance existing timing in RequestLoggingMiddleware:
   - Keep existing `duration_ms` for backward compatibility
   - Add `request_size_bytes` using `len(await request.body())` when body logging enabled
   - Add `response_size_bytes` from captured response body
   - Add process memory delta using `tracemalloc.get_traced_memory()` diff
   - Track active asyncio tasks count via `len(asyncio.all_tasks())`

2. Add performance thresholds to LogConfig:
   - `slow_request_threshold_ms`: int = Field(default=1000, gt=0, description="Log warning if request slower")
   - `critical_request_threshold_ms`: int = Field(default=5000, gt=0, description="Log error if request slower")

3. Enhance the `request_completed` log to include:
   ```python
   # Existing: method, path, status_code, duration_ms, correlation_id
   # Add: request_size_bytes, response_size_bytes, memory_delta_mb, active_tasks
   # Add severity based on thresholds
   ```

4. Integration with OpenTelemetry spans:
   - Add performance attributes to existing spans
   - Use span events for threshold violations

**Implementation Notes**:
- Don't create new classes, enhance existing middleware
- Use existing patterns like `self.logger.info("request_completed", **log_data)`
- Size calculation only when body logging is enabled (performance optimization)
- Memory tracking should be optional (tracemalloc has overhead)

**Testing Approach**:
- Enhance tests in `tests/unit/api/middleware/request_logging/` directory
- Mock `time.time()` and `tracemalloc` calls
- Test threshold severity escalation
- Verify backward compatibility of logs

**Acceptance Criteria**:
- Existing logs remain unchanged (backward compatible)
- New metrics added only when enabled
- Threshold warnings work correctly
- Integration with OpenTelemetry spans

**Implementation Summary**:
Task 2.1 has been successfully implemented with the following enhancements:

1. **Performance Metrics Added**:
   - Request/response size tracking when body logging is enabled
   - Memory delta tracking (optional, disabled by default due to tracemalloc overhead)
   - Active asyncio tasks monitoring for leak detection
   - Configurable slow request threshold (default 1000ms) triggers warnings
   - Critical slowness threshold (default 5000ms) triggers error logs

2. **Configuration Updates**:
   - Added `slow_request_threshold_ms` and `critical_request_threshold_ms` to `LogConfig`
   - Added `enable_memory_tracking` flag for opt-in memory monitoring
   - Updated `.env.example` with performance monitoring environment variables

3. **Logging Enhancements**:
   - `request_completed` logs now include performance metrics
   - Severity escalation based on duration thresholds (info → warning → error)
   - Backward compatible - existing log structure preserved

4. **OpenTelemetry Integration**:
   - Performance attributes added to spans (duration, sizes, memory delta, active tasks)
   - Span events added for threshold violations
   - Proper checking for recording spans to avoid overhead

5. **Testing**:
   - Comprehensive test suite in `test_performance_metrics.py`
   - Tests for threshold violations, memory tracking, OpenTelemetry integration
   - Mocking of time.time() and tracemalloc for deterministic tests

The implementation follows all architectural patterns, maintains backward compatibility, and provides valuable performance insights without significant overhead.

---

### Task 2.2: Async Database Query Performance Tracking
**Status**: ✅ completed
**Files to modify**:
- `src/infrastructure/database/session.py`
- `src/infrastructure/database/dependencies.py`

**Current State**:
- Using async SQLAlchemy with asyncpg driver
- Engine created in `get_engine()` with connection pooling
- OpenTelemetry SQLAlchemy instrumentation available but not enabled
- Database dependency injection via `DatabaseSession`

**Functional Requirements**:
1. Enable OpenTelemetry SQLAlchemy instrumentation in `get_engine()`:
   ```python
   from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

   # After engine creation:
   if settings.log_config.enable_sql_logging:
       SQLAlchemyInstrumentor().instrument(
           engine=engine.sync_engine,
           enable_commenter=True,
           commenter_options={"opentelemetry_values": True}
       )
   ```

2. Add custom event listeners for detailed logging:
   - Use `event.listen()` on the sync_engine for compatibility
   - Track query execution time
   - Log queries exceeding `slow_query_threshold_ms`
   - Include correlation ID from `RequestContext.get_correlation_id()`
   - Sanitize parameters using existing `sanitize_context()`

3. Enhance DatabaseSession context manager to track metrics:
   - Count queries per request
   - Track cumulative query time
   - Store in logger context via `bind_logger_context()`
   - Clean up in finally block

4. Add query info to request completion logs:
   - Modify RequestLoggingMiddleware to include db stats
   - Get stats from logger context before clearing

**Implementation Notes**:
- Event listeners must work with async engine's sync_engine property
- Use `before_cursor_execute` and `after_cursor_execute` events
- Don't log every query by default (too verbose)
- Only log slow queries and aggregated stats
- Leverage OpenTelemetry for detailed tracing

**Testing Approach**:
- Integration tests with real database
- Test slow query detection
- Verify correlation ID propagation
- Test with database fixtures from `conftest.py`

**Acceptance Criteria**:
- OpenTelemetry instrumentation works correctly
- Slow queries logged with full context
- Query statistics in request logs
- No performance regression in query execution

**Implementation Summary**:
Task 2.2 has been successfully implemented with the following enhancements:

1. **OpenTelemetry SQLAlchemy Instrumentation**:
   - Added automatic instrumentation in `create_database_engine()` when SQL logging is enabled
   - Includes commenter support for better trace correlation
   - Graceful handling if instrumentation fails

2. **Custom Event Listeners**:
   - `_before_cursor_execute`: Captures query start time
   - `_after_cursor_execute`: Calculates duration, logs slow queries, updates metrics
   - Slow query logging includes sanitized parameters and correlation IDs
   - Configurable threshold via `slow_query_threshold_ms`

3. **Query Metrics Tracking**:
   - Metrics aggregated in logger context: `db_query_count`, `db_query_duration_ms`
   - `get_db()` dependency tracks session-specific metrics
   - Metrics automatically cleared after each request

4. **Integration with Request Logging**:
   - RequestLoggingMiddleware reads database metrics from logger context
   - Adds metrics to both logs and OpenTelemetry spans
   - Calculates average query time for better insights

5. **Testing**:
   - Comprehensive unit tests for event listeners and instrumentation
   - Integration tests verify end-to-end functionality
   - Tests confirm no performance regression

The implementation seamlessly integrates with the existing logging and observability infrastructure, providing valuable database performance insights without adding significant overhead.

---

### Task 2.3: OpenTelemetry Metrics Integration
**Status**: pending
**Files to modify**:
- `src/core/observability.py`
- `src/api/main.py` (lifespan context)
- `src/api/middleware/request_logging.py`

**Current State**:
- OpenTelemetry API/SDK already installed
- Tracing configured but metrics not yet enabled
- GCP exporter configured for traces
- Lifespan context available for background tasks

**Functional Requirements**:
1. Enhance `setup_tracing()` to include metrics setup:
   - Create MeterProvider with GCP metrics exporter
   - Configure metric readers and views
   - Add runtime metrics collection
   - Use same GCP project configuration

2. Add system metrics collection:
   - Process CPU percentage (via `psutil` if available)
   - Memory usage (RSS, available via `resource` module)
   - Active asyncio tasks count
   - Database pool metrics from `engine.pool.status()`
   - Garbage collection stats

3. Create metric instruments in appropriate locations:
   - Request counter and histogram in RequestLoggingMiddleware
   - Database query counter and duration histogram
   - Custom business metrics hooks
   - Error rate counter in error_handler

4. Add background metric collection task in lifespan:
   - Periodic collection every 60 seconds
   - Non-blocking async task
   - Graceful shutdown on app termination
   - Log warnings if thresholds exceeded

**Implementation Notes**:
- Use OpenTelemetry's semantic conventions for metric names
- Leverage existing correlation IDs as metric attributes
- Don't create custom monitoring classes
- Integrate with GCP Cloud Monitoring for visualization
- Make metrics collection optional via config

**Testing Approach**:
- Mock metric instruments in tests
- Test metric collection doesn't block
- Verify graceful shutdown
- Test with missing optional dependencies

**Acceptance Criteria**:
- Metrics exported to GCP Cloud Monitoring
- No performance impact on request handling
- Graceful degradation if deps missing
- Correlates with distributed traces

---

### Task 2.4: Performance Metadata and Trace Enhancement
**Status**: pending
**Files to modify**:
- `src/api/middleware/request_logging.py`
- `src/core/observability.py`
- `src/api/main.py` (_add_correlation_id_to_span enhancement)

**Current State**:
- Basic OpenTelemetry spans created for requests
- Correlation IDs added to spans
- GCP Cloud Trace handles percentile analysis
- FastAPIInstrumentor adds basic HTTP attributes

**Functional Requirements**:
1. Enhance span attributes for better analysis:
   - Add custom attributes to support Cloud Trace insights
   - Include user ID, tenant ID when available
   - Add request priority/type classification
   - Include cache hit/miss information
   - Add feature flags or experiment IDs

2. Create span events for key milestones:
   - Database connection acquired/released
   - External API calls started/completed
   - Cache lookups performed
   - Business logic checkpoints

3. Enhance the `_add_correlation_id_to_span` function:
   ```python
   # Current: adds correlation_id and http.target
   # Add: request size, response size, endpoint tags
   # Add: user context, request metadata
   ```

4. Add trace sampling configuration:
   - Use TraceIdRatioBased sampler from config
   - Different sampling rates per endpoint
   - Always sample errors and slow requests
   - Respect upstream sampling decisions

**Implementation Notes**:
- Don't calculate percentiles in-process
- Cloud Trace provides automatic latency analysis
- Focus on adding rich metadata for filtering
- Use span events instead of separate log entries
- Leverage trace context propagation

**Testing Approach**:
- Test span attributes are added correctly
- Verify sampling decisions
- Test trace context propagation
- Mock OpenTelemetry in unit tests

**Acceptance Criteria**:
- Rich metadata enables Cloud Trace analysis
- Sampling reduces overhead in production
- Error traces always captured
- No performance regression

---

## Implementation Summary

This performance monitoring plan is specifically designed for this codebase:

1. **Builds on Existing Infrastructure**:
   - Enhances RequestLoggingMiddleware rather than creating new classes
   - Uses OpenTelemetry for metrics instead of custom monitors
   - Leverages GCP Cloud Trace for analysis instead of in-memory percentiles

2. **Follows Project Patterns**:
   - Uses dependency injection and configuration
   - Maintains async patterns throughout
   - Integrates with correlation IDs
   - Respects the clean architecture layers

3. **Testing Approach**:
   - Enhances existing test files
   - Uses established fixtures and mocks
   - Maintains 100% coverage requirement

4. **Avoids Generic Solutions**:
   - No generic ResourceMonitor class
   - No in-memory percentile tracking
   - Specific to FastAPI + SQLAlchemy + OpenTelemetry stack
   - Tailored for GCP deployment
