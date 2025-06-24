# Task 6: Advanced Features

## Overview
Implement advanced logging features including audit trails, dynamic configuration, and developer experience improvements that integrate with the existing FastAPI architecture and logging infrastructure.

## Project Context

### Current State
- **Architecture**: Clean three-layer pattern (API, Core, Infrastructure)
- **Logging**: Structured logging with structlog, correlation IDs, and OpenTelemetry integration
- **API Structure**: Currently only basic endpoints in `main.py`, no routers yet
- **Database**: Async SQLAlchemy with repository pattern
- **Error Handling**: TributumError hierarchy with severity levels
- **No Admin Features**: No admin endpoints or audit system yet

### Architecture Patterns to Follow
- Use APIRouter when adding new endpoint groups
- Leverage existing dependency injection patterns
- Integrate with RequestContext for correlation
- Use repository pattern for data persistence
- Maintain 100% test coverage requirement

## Tasks

### Task 6.1: Audit Logging System
**Status**: pending
**Files to create/modify**:
- Create: `src/core/audit/__init__.py`
- Create: `src/core/audit/events.py`
- Create: `src/core/audit/service.py`
- Create: `src/infrastructure/database/models/audit_log.py`
- Create: `src/api/middleware/audit.py`
- Modify: `src/core/types.py` (add audit types)

**Functional Requirements**:
1. Define audit event types in `events.py`:
   ```python
   class AuditEvent(BaseModel):
       event_id: str  # UUID
       correlation_id: str  # From RequestContext
       event_type: AuditEventType
       severity: ErrorSeverity  # Reuse from exceptions.py
       actor: str | None
       resource: str | None
       action: str
       outcome: Literal["SUCCESS", "FAILURE", "ERROR"]
       metadata: dict[str, Any]
       timestamp: datetime
   ```

2. Create `AuditService` that:
   - Integrates with existing `get_logger()` and `log_exception()`
   - Uses correlation IDs from RequestContext automatically
   - Leverages ORJSONRenderer for serialization
   - Writes to both logs and database (via repository pattern)
   - Respects LogConfig settings for sensitive data filtering

3. Implement `AuditMiddleware` that:
   - Captures all API requests with configurable rules
   - Integrates with existing middleware pipeline
   - Uses existing sanitize_context for request/response bodies
   - Skips paths in log_config.excluded_paths

4. Create `AuditLogRepository` following existing patterns:
   - Extends BaseRepository
   - Async operations only
   - Includes query methods for audit trail retrieval

**Implementation Notes**:
- No cryptographic signatures initially - rely on database immutability
- Use existing TributumError for audit failures
- Integrate with existing structured logging processors
- Audit events should appear in regular logs AND dedicated audit table

**Testing Approach**:
- Unit tests for AuditEvent validation
- Test middleware integration with existing stack
- Test repository operations with test database
- Integration tests for full audit trail
- Test correlation ID propagation

**Acceptance Criteria**:
- Audit events include correlation IDs automatically
- Integration with existing logging infrastructure
- No performance degradation (< 5ms overhead)
- Works with existing error handling
- 100% test coverage maintained

---

### Task 6.2: Dynamic Log Level Management
**Status**: pending
**Files to create/modify**:
- Create: `src/core/admin/__init__.py`
- Create: `src/core/admin/logging_manager.py`
- Create: `src/api/admin/__init__.py`
- Create: `src/api/admin/router.py`
- Create: `src/api/schemas/admin.py`
- Modify: `src/api/main.py` (add admin router)

**Functional Requirements**:
1. Create `LoggingManager` service in core layer:
   ```python
   class LoggingManager:
       def get_current_levels() -> dict[str, str]
       def set_module_level(module: str, level: str) -> None
       def reset_module_level(module: str) -> None
       def get_active_overrides() -> dict[str, LogOverride]
   ```
   - Uses Python's logging.getLogger() for module-specific levels
   - Integrates with structlog's stdlib integration
   - Stores overrides in memory (later can add persistence)

2. Create admin APIRouter:
   ```python
   admin_router = APIRouter(prefix="/admin", tags=["admin"])
   ```
   - `GET /admin/logging/levels` - Get all current levels
   - `PUT /admin/logging/levels/{module}` - Set specific module level
   - `DELETE /admin/logging/levels/{module}` - Reset to default
   - `GET /admin/logging/config` - Get current LogConfig

3. Add request/response schemas:
   - Use existing Pydantic patterns
   - Include validation for log levels
   - Return standardized responses using ORJSONResponse

4. Integrate with existing systems:
   - Changes trigger audit events (if Task 6.1 complete)
   - Include correlation_id in admin operations
   - Use existing error handling patterns

**Implementation Notes**:
- Start with in-memory storage, no persistence
- Use existing Settings/LogConfig as source of truth for defaults
- Admin endpoints need authentication (stub for now)
- Changes apply immediately via logging module

**Testing Approach**:
- Unit test LoggingManager operations
- Test API endpoints with TestClient
- Verify level changes take effect
- Test invalid module names and levels
- Integration test with actual logging output

**Acceptance Criteria**:
- Module-specific levels work correctly
- No restart required for changes
- Existing logs unaffected by new module levels
- Admin API follows project patterns
- Graceful handling of invalid inputs

---

### Task 6.3: Log Metrics and Monitoring Integration
**Status**: pending
**Files to create/modify**:
- Create: `src/core/monitoring/log_metrics.py`
- Create: `src/core/monitoring/collectors.py`
- Modify: `src/core/observability.py` (add log metrics)
- Modify: `src/api/admin/router.py` (add metrics endpoints)
- Create: `src/api/schemas/metrics.py`

**Functional Requirements**:
1. Create `LogMetricsCollector` that:
   ```python
   class LogMetricsCollector:
       def __init__(self):
           self.error_counts: dict[str, int]  # By error_code
           self.request_counts: dict[str, int]  # By endpoint
           self.response_times: dict[str, list[float]]  # By endpoint
           self.correlation_index: dict[str, list[LogEntry]]  # By correlation_id
   ```
   - Integrates with existing logging processors
   - Maintains rolling windows (1h, 24h)
   - Calculates percentiles using existing patterns
   - Memory-efficient circular buffers

2. Enhance observability.py:
   - Add OpenTelemetry metrics for log events
   - Export error rates, request rates
   - Include log-specific metrics (sampling rate, drop rate)
   - Integrate with existing tracer setup

3. Create metrics API endpoints:
   - `GET /admin/metrics/logs` - Current log metrics
   - `GET /admin/metrics/errors` - Error breakdown by type
   - `GET /admin/metrics/performance` - Response time percentiles
   - `GET /admin/trace/{correlation_id}` - Get all logs for correlation ID

4. Add real-time monitoring:
   - Hook into existing RequestLoggingMiddleware
   - Track metrics without impacting performance
   - Use existing error severity levels for prioritization

**Implementation Notes**:
- Reuse existing performance tracking patterns
- Leverage correlation IDs for request tracing
- Use ORJSONRenderer for metrics serialization
- Keep memory usage bounded with sliding windows

**Testing Approach**:
- Unit test metric calculations
- Test memory bounds with high volume
- Test API response formats
- Verify integration with OpenTelemetry
- Performance test metric collection overhead

**Acceptance Criteria**:
- Metrics collection < 1ms overhead
- Memory usage remains constant
- Correlation ID lookup works correctly
- Integrates with existing observability
- Useful for debugging production issues

---

### Task 6.4: Developer Experience Enhancements
**Status**: pending
**Files to create/modify**:
- Create: `src/core/dev_tools/__init__.py`
- Create: `src/core/dev_tools/log_inspector.py`
- Create: `scripts/log_tools.py`
- Modify: `src/core/logging.py` (add dev mode enhancements)
- Modify: `Makefile` (add log analysis commands)

**Functional Requirements**:
1. Create `LogInspector` for development:
   ```python
   class LogInspector:
       def get_logs_by_correlation_id(correlation_id: str) -> list[LogEntry]
       def get_request_trace(correlation_id: str) -> RequestTrace
       def format_for_console(logs: list[LogEntry]) -> str
       def export_trace(correlation_id: str, format: Literal["json", "markdown"]) -> str
   ```
   - Works with in-memory log buffer in dev mode
   - Integrates with existing correlation ID system
   - Uses existing ORJSONRenderer for exports

2. Enhance dev mode logging:
   - Add optional in-memory circular buffer for recent logs
   - Include local variables in exception logs (dev only)
   - Add timing breakdown for middleware pipeline
   - Show SQL queries inline (when enable_sql_logging=True)

3. Create CLI tools in scripts/:
   ```bash
   # In Makefile:
   log-inspect:  ## Inspect logs by correlation ID
       uv run python scripts/log_tools.py inspect $(CORRELATION_ID)

   log-errors:  ## Show recent errors with context
       uv run python scripts/log_tools.py errors --last=10

   log-trace:  ## Export full request trace
       uv run python scripts/log_tools.py trace $(CORRELATION_ID) --format=markdown
   ```

4. Add development-specific endpoints:
   - `GET /dev/logs/recent` - Recent logs (dev mode only)
   - `GET /dev/logs/correlation/{id}` - Logs for correlation ID
   - `GET /dev/logs/errors` - Recent errors with stack traces
   - Protected by DEBUG=true check

**Implementation Notes**:
- Dev tools only active when settings.debug=True
- Reuse existing error context and correlation systems
- Memory buffer limited to prevent leaks
- Pretty formatting uses existing ConsoleRenderer
- CLI tools use existing project patterns (like scripts/tool)

**Testing Approach**:
- Test LogInspector with mock data
- Test memory buffer limits
- Test CLI tool commands
- Verify dev endpoints only in debug mode
- Test export formats

**Acceptance Criteria**:
- Zero impact on production performance
- Correlation ID tracing works end-to-end
- CLI tools follow project conventions
- Memory usage bounded in dev mode
- Helpful for debugging without external tools

---

## Implementation Notes

### Integration with Existing Infrastructure

These advanced features are designed to leverage the existing codebase:

1. **Audit System** builds on:
   - Existing correlation ID propagation via RequestContext
   - TributumError hierarchy for error handling
   - Repository pattern for data persistence
   - Structured logging with sensitive data filtering

2. **Admin Features** follow patterns:
   - APIRouter for organizing endpoints (first router in the project)
   - Dependency injection for services
   - Pydantic schemas for validation
   - ORJSONResponse for consistency

3. **Monitoring** extends:
   - Existing OpenTelemetry integration
   - RequestLoggingMiddleware metrics
   - Performance tracking patterns
   - Error severity levels

4. **Dev Tools** enhance:
   - Existing debug mode configuration
   - Correlation ID system for tracing
   - Makefile patterns for CLI tools
   - Scripts directory conventions

### Key Design Decisions

1. **No new external dependencies** - Everything builds on existing libraries
2. **Memory-first approach** - Start simple, add persistence later
3. **Progressive enhancement** - Each feature works standalone
4. **Production safety** - Dev tools only in debug mode
5. **Performance conscious** - All features respect < 5ms overhead goal

### Testing Strategy

Following the project's 100% coverage requirement:
- Unit tests for all new services and utilities
- Integration tests with existing middleware
- API tests using TestClient
- Performance benchmarks for overhead
- Use existing fixtures and patterns

### Success Metrics

- Audit trail captures all critical operations
- Admin API enables runtime log management
- Metrics provide actionable insights
- Dev tools reduce debugging time
- No regression in performance or stability
