# Task 1: Foundation - Enhanced Logging Configuration

## Overview
Enhance the base logging configuration to support advanced features while maintaining backward compatibility. This task establishes the foundation for all subsequent logging improvements.

## Project Context

### Current Logging Implementation
The project has a sophisticated logging system built on structlog with the following key components:

1. **Configuration** (`src/core/config.py`):
   - `LogConfig` class (Pydantic BaseModel) with settings for log level, format, timestamps
   - Nested configuration using `__` delimiter for environment variables
   - Configuration post-initialization adjusts settings based on environment

2. **Core Logging** (`src/core/logging.py`):
   - Custom `ORJSONRenderer` for high-performance JSON serialization
   - Context management using Python's `contextvars` for async-safe propagation
   - Existing processors: `add_log_level_upper`, `inject_correlation_id`, `inject_logger_context`
   - Helper functions: `bind_logger_context()`, `clear_logger_context()`, `log_exception()`
   - Context manager: `log_context()` for temporary bindings

3. **Request Logging** (`src/api/middleware/request_logging.py`):
   - `RequestLoggingMiddleware` with configurable body logging (constructor parameters)
   - Sensitive header redaction
   - Request/response size tracking and duration metrics
   - Integration with correlation IDs from `RequestContext`

4. **Integration Points**:
   - Error handling in `src/api/middleware/error_handler.py` uses `log_exception()`
   - Database session management ready for query logging hooks
   - OpenTelemetry tracing infrastructure in place

### Architecture Patterns
- Clean architecture with three layers (API, Core, Infrastructure)
- Dependency injection using FastAPI's `Depends`
- Middleware pipeline execution order matters
- All configuration through Pydantic Settings with validation
- Type safety enforced (no `# type: ignore` allowed)

## Tasks

### Task 1.1: Enhanced Logging Configuration Model
**Status**: completed
**Files modified**:
- `src/core/config.py`
- `tests/unit/core/config/test_log_config.py`
- `tests/unit/core/config/test_settings.py`
- `tests/unit/core/config/test_settings_env_overrides.py`

**Functional Requirements**:
1. Extend the `LogConfig` class to include:
   - `sampling_rate`: float = Field(default=1.0, ge=0.0, le=1.0, description="Log sampling rate")
   - `enable_async_logging`: bool = Field(default=False, description="Enable async logging")
   - `async_queue_size`: int = Field(default=10000, gt=0, description="Async queue size")
   - `excluded_paths`: list[str] = Field(default_factory=lambda: ["/health", "/metrics"], description="Paths to exclude from logging")
   - `sensitive_fields`: list[str] = Field(default_factory=lambda: ["password", "token", "secret", "api_key", "authorization"], description="Field names to redact")
   - `enable_sql_logging`: bool = Field(default=False, description="Enable SQL query logging")
   - `slow_query_threshold_ms`: int = Field(default=100, gt=0, description="Slow query threshold in milliseconds")
   - `enable_performance_processor`: bool = Field(default=False, description="Add performance metrics to logs")
   - `enable_environment_processor`: bool = Field(default=True, description="Add environment info to logs")
   - `enable_error_context_processor`: bool = Field(default=True, description="Add enhanced error context")

2. Move RequestLoggingMiddleware body logging config to LogConfig:
   - `log_request_body`: bool = Field(default=False, description="Log request bodies")
   - `log_response_body`: bool = Field(default=False, description="Log response bodies")
   - `max_body_log_size`: int = Field(default=10240, gt=0, description="Max body size to log in bytes")

3. Add a `model_post_init` enhancement to set async_logging=True in production automatically

**Implementation Notes**:
- Use Pydantic's Field validators (ge, le, gt) instead of custom validators where possible
- Follow existing pattern of using Field() with descriptions
- Ensure backward compatibility with existing LogConfig fields
- The RequestLoggingMiddleware will need updating to use config instead of constructor params

**Testing Approach**:
- Test all Field validators work correctly
- Test default_factory for list fields
- Test environment variable loading with LOG_CONFIG__ prefix
- Test model_post_init logic for production settings
- Test backward compatibility with existing code

**Acceptance Criteria**:
- All new fields follow existing Pydantic patterns
- Validation uses built-in Pydantic validators
- Environment variables work with nested delimiter
- Production auto-configuration works correctly
- 100% test coverage maintained

**Completion Summary**:
- ✅ All 14 new fields added to LogConfig with proper Field validators
- ✅ Production environment automatically enables async logging
- ✅ Explicit environment variable overrides respected
- ✅ Comprehensive test coverage including validation, defaults, and environment overrides
- ✅ All pre-commit checks pass (linting, type checking, formatting)
- ✅ Backward compatible - existing code continues to work
- ✅ Ready for integration with RequestLoggingMiddleware in Task 1.4

---

### Task 1.2: Enhanced Context Management
**Status**: completed
**Files modified**:
- `src/core/logging.py`
- `tests/unit/core/logging/test_context_binding.py`
- `tests/unit/core/logging/test_context_managers.py`
- `tests/unit/core/logging/test_enhanced_context.py`

**Current State**:
The codebase already has context management using contextvars:
- `_logger_context_var: ContextVar[dict[str, Any] | None]` stores context
- `bind_logger_context(**bindings)` adds context
- `clear_logger_context()` clears context
- `inject_logger_context` processor adds context to all logs
- `log_context()` context manager for temporary bindings

**Functional Requirements**:
1. Enhance the existing context system with better structure:
   - Add `get_logger_context()` function to retrieve current context (currently only internal `_logger_context_var.get()`)
   - Add `unbind_logger_context(*keys)` to remove specific keys without clearing all
   - Add context merging strategies (shallow vs deep merge)
   - Add context size limits to prevent memory issues

2. Create a `LogContextManager` class that wraps the contextvar operations:
   - `push()` - Add a new context layer (for nested contexts)
   - `pop()` - Remove the top context layer
   - `peek()` - Get current context without modification
   - `merge()` - Merge new values with strategy options
   - Track context depth to prevent infinite nesting

3. Enhance `inject_logger_context` processor to:
   - Add context depth indicator
   - Filter out None values
   - Apply size limits with truncation

**Implementation Notes**:
- Build on top of existing `_logger_context_var`, don't replace it
- Maintain backward compatibility with existing functions
- The existing `log_context()` context manager should use the new capabilities
- Consider performance impact of deep merging

**Testing Approach**:
- Test new functions work with existing context
- Test context layering with push/pop
- Test size limits and truncation
- Test merge strategies
- Verify no memory leaks with long-running contexts
- Test async context isolation

**Acceptance Criteria**:
- Existing context functions continue to work
- New capabilities integrate seamlessly
- No performance degradation
- Context size is bounded
- Better visibility into context state

**Completion Summary**:
- ✅ Added `get_logger_context()` function to retrieve current context as a copy
- ✅ Added `unbind_logger_context(*keys)` to remove specific keys from context
- ✅ Created `MergeStrategy` enum with SHALLOW and DEEP options
- ✅ Implemented `LogContextManager` class with push/pop/peek/merge operations
- ✅ Added context size limits with constants: MAX_CONTEXT_SIZE (10KB), MAX_CONTEXT_DEPTH (10), MAX_VALUE_SIZE (1KB)
- ✅ Enhanced `inject_logger_context` processor to:
  - Filter None values automatically
  - Add context_depth when using LogContextManager
  - Truncate large values with "..." indicator
  - Add context_truncated flag when total size exceeded
- ✅ Enhanced `log_context()` to use LogContextManager while maintaining backward compatibility
- ✅ Deep copy support in LogContextManager to prevent mutations
- ✅ Comprehensive test coverage including async compatibility
- ✅ All pre-commit checks pass (fixed pydoclint issue)
- ✅ Backward compatible - existing code continues to work

---

### Task 1.3: Enhanced Log Processors
**Status**: completed
**Files modified**:
- `src/core/logging.py`
- `src/core/constants.py`
- `tests/unit/core/logging/test_processors.py`
- `pyproject.toml`

**Current State**:
Existing processors follow the structlog pattern:
```python
def processor(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
```
Current processors: `add_log_level_upper`, `inject_correlation_id`, `inject_logger_context`

**Functional Requirements**:
1. Create a `PerformanceProcessor` that adds:
   - `process_id`: int (using os.getpid())
   - `thread_id`: str (using threading.get_ident())
   - `memory_mb`: float (RSS memory using psutil if available, graceful fallback)
   - `active_tasks`: int (count of asyncio tasks if in async context)

2. Create an `EnvironmentProcessor` that adds:
   - `hostname`: str (using socket.gethostname())
   - `container_id`: str | None (parse from /proc/self/cgroup if exists)
   - `k8s_pod`: str | None (from K8S_POD_NAME env var)
   - `k8s_namespace`: str | None (from K8S_NAMESPACE env var)
   - Cache these values as they don't change

3. Create an `ErrorContextProcessor` that enhances exception logging:
   - Works with existing `format_exc_info` and `dict_tracebacks` processors
   - Adds `exception_fingerprint`: str (hash of exception type + key stack frames)
   - Adds `exception_module`: str (module where exception originated)
   - Integrates with existing `sanitize_context` from error_context.py
   - Only processes when `exc_info` is present in event_dict

4. Integration approach:
   - Add processors to both dev_processors and prod_processors lists
   - Maintain correct order: new processors should run after base processors but before formatting
   - Use LogConfig flags to conditionally include processors

**Implementation Notes**:
- All processors must handle missing dependencies gracefully (e.g., psutil not installed)
- Use try/except blocks for system calls that might fail
- Cache expensive operations (hostname, container detection)
- Follow existing pattern of using `_` for unused parameters
- Processors should be fast - avoid blocking I/O

**Testing Approach**:
- Mock system calls (os.getpid, socket.gethostname, etc.)
- Test with and without optional dependencies
- Test processor integration order
- Test performance impact < 0.1ms per processor
- Test exception processor with various exception types

**Acceptance Criteria**:
- All processors follow structlog interface
- Graceful degradation when system info unavailable
- No errors when optional dependencies missing
- Cached values work correctly
- Performance overhead minimal

**Completion Summary**:
- ✅ All three processors implemented with proper structlog interface
- ✅ `performance_processor`: Adds process_id, thread_id, memory_mb (with psutil), active_tasks
- ✅ `environment_processor`: Adds hostname, container_id, k8s_pod, k8s_namespace with caching
- ✅ `error_context_processor`: Adds exception_fingerprint, exception_module, integrates with sanitize_context
- ✅ Constants properly defined: MIN_CONTAINER_ID_LENGTH, EXCEPTION_TUPLE_MIN_LENGTH, TRACEBACK_FRAMES_TO_INCLUDE
- ✅ psutil added as dependency (v7.0.0) for memory monitoring
- ✅ All processors handle errors gracefully with try/except blocks
- ✅ Environment values cached to avoid repeated system calls
- ✅ Comprehensive test coverage (100%) with pytest-mock
- ✅ All pre-commit checks pass
- ✅ Ready for integration in Task 1.4

**Note**: Processors are implemented but not yet integrated into `configure_structlog()`. This integration is intentionally left for Task 1.4 as per the specification.

---

### Task 1.4: Configuration-based Processor Selection and Middleware Integration
**Status**: completed
**Files modified**:
- `src/core/logging.py`
- `src/api/main.py`
- `src/api/middleware/request_logging.py`
- `tests/unit/api/middleware/request_logging/conftest.py`
- `tests/unit/api/middleware/request_logging/test_basic_logging.py`
- `tests/unit/api/middleware/request_logging/test_response_body_logging.py`

**Current State**:
- `configure_structlog()` already conditionally selects processors based on log format
- RequestLoggingMiddleware is instantiated with hardcoded parameters in main.py
- Processor order: base → timestamp → format-specific → renderer

**Functional Requirements**:
1. Modify `configure_structlog()` to use new LogConfig fields:
   ```python
   if log_config.enable_performance_processor:
       base_processors.append(performance_processor)
   if log_config.enable_environment_processor:
       base_processors.append(environment_processor)
   if log_config.enable_error_context_processor:
       base_processors.append(error_context_processor)
   ```

2. Update RequestLoggingMiddleware instantiation in `create_app()`:
   - Remove hardcoded constructor parameters
   - Pass settings.log_config for body logging settings
   - Update middleware to read from LogConfig

3. Implement path exclusion in RequestLoggingMiddleware:
   - Check request.url.path against log_config.excluded_paths
   - Skip logging for excluded paths
   - Still propagate correlation ID for excluded paths

4. Ensure correct processor order:
   - Standard processors (logger name, level)
   - Context injection (correlation ID, logger context)
   - New processors (performance, environment, error)
   - Formatting processors (timestamp, callsite)
   - Renderers (ConsoleRenderer or ORJSONRenderer)

**Implementation Notes**:
- The new processors go into base_processors list after context injection
- RequestLoggingMiddleware needs access to Settings via dependency injection or constructor
- Path exclusion should be case-insensitive
- Maintain existing behavior when new features are disabled

**Testing Approach**:
- Test processor inclusion/exclusion based on config
- Test middleware uses config for body logging
- Test path exclusion works correctly
- Test processor order is maintained
- Integration test with full middleware stack

**Acceptance Criteria**:
- All processors controlled by configuration
- RequestLoggingMiddleware uses central config
- Path exclusion works as expected
- No breaking changes to existing logs
- Clean integration with existing code

**Completion Summary**:
- ✅ `configure_structlog()` in `src/core/logging.py` now conditionally adds `performance_processor`, `environment_processor`, and `error_context_processor` based on `LogConfig` flags.
- ✅ `RequestLoggingMiddleware` instantiation in `src/api/main.py` correctly passes the `log_config` object.
- ✅ `RequestLoggingMiddleware` in `src/api/middleware/request_logging.py` correctly uses the `log_config` for path exclusion and body logging settings.
- ✅ Fixed `NameError` and `TypeError` issues in the test suite to ensure all tests pass.
- ✅ All pre-commit checks pass, and test coverage is maintained at >99%.
- ✅ The integration is complete and all acceptance criteria are met.

---

## Implementation Dependencies and Order

### Dependencies Between Tasks
1. **Task 1.1** (Config Model) must be completed first as other tasks depend on the new configuration fields
2. **Task 1.2** (Context Enhancement) is independent but should be done early as it improves all logging
3. **Task 1.3** (Processors) depends on Task 1.1 for the enable flags
4. **Task 1.4** (Integration) depends on Tasks 1.1 and 1.3 and ties everything together

### External Dependencies
- No new required dependencies
- Optional: `psutil` for memory monitoring in PerformanceProcessor (graceful fallback if not present)
- Existing: `structlog`, `orjson`, `pydantic` (already in project)

### Testing Strategy
1. **Unit Tests** for each component:
   - Config validation in `tests/unit/core/config/` directory (modular test files)
   - New processors in `tests/unit/core/logging/test_processors.py`
   - Context enhancements in `tests/unit/core/logging/` test modules

2. **Integration Tests**:
   - Full logging pipeline in `tests/integration/api/test_middleware_integration.py`
   - Config changes affecting logs in `tests/integration/test_config_integration.py`

3. **Performance Tests**:
   - Benchmark logging overhead before/after changes
   - Ensure < 1ms impact on request processing

### Rollback Plan
Each task is designed to be backward compatible:
- New config fields have defaults matching current behavior
- Existing functions are enhanced, not replaced
- Feature flags allow disabling new functionality
- No database migrations or state changes

### Success Metrics
- No regression in existing functionality
- 100% test coverage maintained
- Performance overhead < 1ms per request
- All new features configurable via environment variables
- Clean integration with existing patterns
