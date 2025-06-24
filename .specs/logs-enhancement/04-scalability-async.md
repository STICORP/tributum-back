# Task 4: Scalability - Async Logging and Sampling

## Overview
Enhance the existing async-safe logging system with non-blocking writes and intelligent sampling to handle high-volume production workloads without impacting FastAPI's event loop performance.

## Project Context

### Current Architecture
1. **FastAPI Async Foundation**:
   - All endpoints and middleware use `async def`
   - Request processing on asyncio event loop
   - SQLAlchemy configured for async operations
   - No threading - pure async/await pattern

2. **Existing Logging Infrastructure**:
   - Structlog with custom `ORJSONRenderer` for performance
   - Async-safe context propagation via `contextvars`
   - Correlation IDs maintained across async boundaries
   - Synchronous log writes (standard for Python logging)

3. **Performance Optimizations Already Present**:
   - ORJSON for 3x faster JSON serialization
   - Pre-configured processors pipeline
   - Efficient error context sanitization

4. **OpenTelemetry Integration**:
   - Trace context already propagated
   - Correlation IDs linked to spans
   - Error tracking in spans

### Scalability Challenges
While the logging is async-safe, the actual log writes are synchronous and can block the event loop under high load. We need to implement true async logging without breaking the existing patterns.

## Tasks

### Task 4.1: Non-blocking Structlog Writer
**Status**: pending
**Files to modify**:
- `src/core/logging.py` (add async writer class)
- `src/core/config.py` (add async logging config)

**Current State**:
- Structlog uses `stdlib.LoggerFactory()` which writes synchronously
- Log writes can block the FastAPI event loop under high load
- All processors and context management already async-safe

**Functional Requirements**:
1. Create `AsyncStructlogWriter` class that:
   - Implements structlog's processor interface
   - Queues log entries using `asyncio.Queue`
   - Runs a background task on the FastAPI event loop
   - Integrates with existing `ORJSONRenderer`
   - Maintains correlation ID context

2. Implement queue management:
   - Use `LogConfig.async_queue_size` for buffer size
   - When queue full: drop oldest entries (not newest)
   - Track dropped log counts in metrics
   - Flush queue on app shutdown via lifespan

3. Integration with FastAPI:
   - Start background task in `lifespan` context manager
   - Ensure graceful shutdown drains the queue
   - Use `asyncio.create_task()` not threads
   - Respect the single event loop pattern

4. Maintain existing behavior:
   - When `enable_async_logging=False`, use current sync path
   - Preserve all processor outputs
   - Keep correlation ID propagation working

**Implementation Notes**:
- The AsyncStructlogWriter goes at the END of the processor chain
- It replaces the final renderer only when async is enabled
- Use `asyncio.wait_for()` with timeout for queue puts
- Log about dropped entries at WARN level (ironic but necessary)

**Testing Approach**:
- Mock asyncio.Queue to test overflow behavior
- Test correlation ID preservation across async boundary
- Integration test with full FastAPI request
- Benchmark event loop blocking before/after
- Test graceful shutdown drains all logs

**Acceptance Criteria**:
- No blocking of FastAPI event loop
- <0.1ms latency for log calls (just queue put)
- Dropped logs tracked and reported
- Clean shutdown with no log loss
- Existing sync mode still works

---

### Task 4.2: Request-aware Log Sampling
**Status**: pending
**Files to modify**:
- `src/core/logging.py` (add sampling processor)
- `src/api/middleware/request_context.py` (add sampling decision)
- `src/api/middleware/request_logging.py` (respect sampling)

**Current State**:
- Every request gets a correlation ID via RequestContext
- OpenTelemetry trace sampling already exists
- All logs include correlation_id for grouping
- RequestLoggingMiddleware logs all requests

**Functional Requirements**:
1. Create `sampling_processor` for structlog that:
   - Reads sampling decision from RequestContext
   - Uses `LogConfig.sampling_rate` as default
   - Always logs if level >= ERROR (priority sampling)
   - Preserves complete request traces (all logs with same correlation_id)
   - Adds `_sampled: bool` and `_sample_rate: float` to event_dict

2. Enhance RequestContext to store sampling decision:
   - Add `set_sampling_decision(sampled: bool, rate: float)`
   - Add `get_sampling_decision() -> tuple[bool, float]`
   - Decision made once per request and propagated
   - Integrate with OpenTelemetry trace sampling if enabled

3. Implement sampling strategies in RequestContextMiddleware:
   - Random sampling using correlation_id as seed (deterministic)
   - Path-based rules (e.g., always sample /api/v1/payments)
   - Error-triggered sampling (if any error in request, sample all)
   - Health check exclusion (never sample /health)

4. Update RequestLoggingMiddleware to:
   - Check sampling decision before logging
   - Add `X-Log-Sampled` response header (for debugging)
   - Track sampling effectiveness metrics

**Implementation Notes**:
- Sampling decision must be made BEFORE first log in request
- Use correlation_id for consistent randomness: `hash(correlation_id) % 100 < sample_rate * 100`
- The sampling processor should be early in the chain
- Respect `excluded_paths` from LogConfig

**Testing Approach**:
- Test sampling decision consistency within request
- Test priority sampling for errors
- Test deterministic sampling with same correlation_id
- Verify sampling rate accuracy over many requests
- Test with OpenTelemetry integration

**Acceptance Criteria**:
- Exact sampling rate achieved (±1%)
- All logs for a request either kept or dropped together
- Errors never sampled out
- No performance impact on non-sampled requests
- Sampling decision visible in logs

---

### Task 4.3: Repetitive Log Aggregation
**Status**: pending
**Files to modify**:
- `src/core/logging.py` (add aggregation processor)
- `src/infrastructure/database/session.py` (aggregate connection pool logs)

**Current State**:
- High-frequency logs from database pool, health checks
- Each log entry includes full context and correlation_id
- No aggregation of similar messages

**Functional Requirements**:
1. Create `aggregation_processor` for structlog that:
   - Identifies repetitive log patterns (same message, different timestamps)
   - Groups by: (message template, level, correlation_id)
   - Never aggregates across different correlation_ids
   - Preserves first occurrence with full context
   - Tracks count and time window
   - Emits aggregated entry on flush or correlation_id change

2. Aggregation rules:
   - Only aggregate if message repeated >5 times in 1 second
   - Exclude ERROR and CRITICAL levels from aggregation
   - Preserve distinct field values (e.g., different error codes)
   - Maximum aggregation window: 10 seconds
   - Maximum aggregated count: 1000 per entry

3. Smart aggregation for known patterns:
   - Database connection pool: "Connection pool size: X"
   - Health checks: "Health check completed"
   - Metric emissions: "Metric recorded: X"
   - But NOT user-specific actions or business events

4. Aggregated log format:
   ```python
   {
       "message": "Connection pool size: 10",
       "level": "DEBUG",
       "correlation_id": "abc123",
       "_aggregated": True,
       "_count": 47,
       "_first_occurrence": "2024-01-01T10:00:00",
       "_last_occurrence": "2024-01-01T10:00:09",
       "_window_seconds": 9
   }
   ```

**Implementation Notes**:
- Use an LRU cache with max 1000 entries for tracking
- Flush aggregated entries when correlation_id changes
- The processor must maintain order - aggregated logs emitted at end of window
- Memory safety: if cache full, flush oldest entries

**Testing Approach**:
- Test aggregation with rapid repeated logs
- Test correlation_id boundary preservation
- Test memory limits with many unique messages
- Test that business logs aren't aggregated
- Verify aggregation statistics accuracy

**Acceptance Criteria**:
- >50% reduction in log volume for system logs
- No aggregation of user action logs
- Memory usage <10MB for aggregation cache
- Aggregated logs contain accurate counts
- Original log context preserved

---

### Task 4.4: Structlog Performance Optimization
**Status**: pending
**Files to modify**:
- `src/core/logging.py` (optimize processors and renderer)
- `src/api/middleware/request_logging.py` (optimize body handling)
- `src/core/error_context.py` (cache sanitization patterns)

**Current State**:
- ORJSONRenderer already implemented with `OPT_SORT_KEYS`
- Multiple processors run on every log entry
- RequestLoggingMiddleware parses bodies synchronously
- Sanitization runs regex on every call

**Functional Requirements**:
1. Optimize ORJSONRenderer:
   - Add `OPT_PASSTHROUGH_DATETIME` flag (ORJSON handles natively)
   - Remove unnecessary `_process_dict` for simple types
   - Use `OPT_APPEND_NEWLINE` to avoid string concatenation
   - Cache the renderer options calculation

2. Processor optimizations:
   - Cache `CallsiteParameterAdder` frame inspection results
   - Make `inject_correlation_id` check for None before contextvar access
   - Lazy evaluate expensive fields (only compute if log level enabled)
   - Skip processors if their output fields already exist

3. Optimize sanitization in error_context.py:
   - Pre-compile all regex patterns at module level
   - Cache sanitization results for immutable values (use hash)
   - Add fast path for common safe fields
   - Use `__slots__` on any new classes for memory efficiency

4. RequestLoggingMiddleware optimizations:
   - Make body parsing async: `await asyncio.to_thread(json.loads, body)`
   - Stream large response bodies instead of loading fully
   - Skip body logging for binary content types early
   - Use memory view for body truncation instead of slicing

**Implementation Notes**:
- Benchmark each optimization individually
- The ORJSONRenderer is already fast, focus on processor overhead
- Use `@lru_cache` sparingly - consider memory vs speed tradeoff
- Profile with `py-spy` to find actual bottlenecks

**Testing Approach**:
- Benchmark logging throughput: before vs after
- Memory profiling with `tracemalloc`
- Test with 10K logs/second load
- Verify no behavior changes with property tests
- Check cache hit rates with metrics

**Acceptance Criteria**:
- 30% reduction in P99 logging latency
- No increase in memory usage
- Backwards compatible output
- All optimizations documented
- Performance metrics exposed

---

## Implementation Dependencies and Order

### Task Dependencies
1. **Task 4.4** (Performance Optimization) should be done FIRST
   - Establishes performance baseline
   - Optimizations benefit all other tasks
   - No dependencies on other scalability features

2. **Task 4.2** (Request-aware Sampling) next
   - Reduces log volume immediately
   - Simpler than async writing
   - Benefits from Task 4.4's optimizations

3. **Task 4.3** (Aggregation) third
   - Further reduces log volume
   - Combines well with sampling
   - Still synchronous, so simpler

4. **Task 4.1** (Async Writer) last
   - Most complex change
   - Benefits from reduced volume (sampling + aggregation)
   - Requires changes to app lifecycle

### Integration Points
1. **With FastAPI Architecture**:
   - All async code uses the single event loop
   - No threads or multiprocessing
   - Lifecycle managed in `lifespan` context manager
   - Middleware pipeline order matters

2. **With Existing Logging**:
   - Structlog processors run in order
   - Context propagated via contextvars
   - ORJSONRenderer already optimized
   - Correlation IDs link all logs per request

3. **With OpenTelemetry**:
   - Trace sampling can influence log sampling
   - Correlation IDs already in spans
   - Performance metrics can go to traces

### Performance Considerations
- **Current State**: ~0.5-1ms per log entry
- **After Optimization**: Target <0.3ms
- **After Sampling**: 70% fewer logs to process
- **After Aggregation**: 50% fewer system logs
- **After Async**: Near-zero blocking time

### Testing Strategy
1. **Performance Baseline**:
   - Benchmark current implementation
   - Use `pytest-benchmark` for consistency
   - Profile with `py-spy` under load

2. **Load Testing**:
   - Use `locust` to generate realistic load
   - Test with 1K, 10K, 100K requests/second
   - Monitor event loop lag

3. **Integration Testing**:
   - Full request flow with all features
   - Verify correlation ID preservation
   - Check graceful degradation

### Rollback Safety
- Each task can be disabled via configuration
- Async logging falls back to sync if needed
- Sampling can be set to 100% (disabled)
- All changes are backwards compatible

### Success Metrics
- **Latency**: P99 <0.3ms for log calls
- **Throughput**: Handle 100K logs/second
- **CPU Usage**: <5% overhead for logging
- **Memory**: <50MB for all caches/buffers
- **Reliability**: Zero log loss under normal load
