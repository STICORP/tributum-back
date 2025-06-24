# Task 5: External Integrations

## Overview
Add support for external logging services and observability platforms while maintaining flexibility to switch providers.

## Project Context

### Current Infrastructure
1. **Deployment Target**: Google Cloud Platform (GCP)
   - Terraform configurations in `terraform/` for GCP resources
   - Designed for Cloud Run deployment (containerized)
   - Currently logs to stdout (standard for container deployments)

2. **Existing Observability** (`src/core/observability.py`):
   - OpenTelemetry already integrated with GCP Cloud Trace
   - Custom `ErrorTrackingSpanProcessor` for error context
   - Configurable via `ObservabilityConfig` in settings
   - FastAPI instrumentation active

3. **Logging Output**:
   - All logs currently go to `sys.stdout` via structlog
   - JSON format in production for machine parsing
   - No external log shipping implemented

4. **Architecture Patterns**:
   - Flat structure in `src/core/` (no subdirectories)
   - Configuration via Pydantic Settings
   - Clean separation of concerns

### Integration Requirements
- Build upon existing OpenTelemetry infrastructure
- Maintain stdout logging for container compatibility
- Support both GCP-native and vendor-neutral options
- Preserve correlation between logs and traces

## Tasks

### Task 5.1: Structlog Handler Extensions
**Status**: pending
**Files to modify**:
- `src/core/logging.py` (add handler classes at module level)
- Create: `src/core/log_handlers.py` (following flat structure pattern)

**Current State**:
- Structlog outputs to stdout via `logging.basicConfig`
- No custom handlers implemented
- Must maintain stdout for Cloud Run/container compatibility

**Functional Requirements**:
1. Create abstract `BaseLogHandler` class in `log_handlers.py`:
   ```python
   class BaseLogHandler(Protocol):
       async def emit(self, event_dict: EventDict) -> None: ...
       async def flush(self) -> None: ...
       async def close(self) -> None: ...
   ```

2. Create `HandlerChain` class to manage multiple handlers:
   - Always includes stdout handler (non-removable)
   - Add/remove additional handlers dynamically
   - Handle failures without affecting stdout
   - Async-safe operations

3. Implement basic handlers:
   - `StdoutHandler` - Current behavior (always active)
   - `BufferedHandler` - Base class for batching
   - `MetricsHandler` - Emit log metrics
   - Keep handlers in `log_handlers.py` (not nested directories)

4. Integrate with structlog via custom processor:
   - Add `emit_to_handlers` processor at end of pipeline
   - Maintains existing stdout behavior
   - Adds additional handler emissions

**Implementation Notes**:
- Handlers are additive to stdout, not replacements
- Use asyncio for non-blocking handler operations
- Follow existing pattern of keeping modules flat in core/
- Respect the existing ORJSONRenderer for serialization

**Testing Approach**:
- Test handler protocol compliance
- Test chain with multiple handlers
- Test failure isolation
- Verify stdout always works

**Acceptance Criteria**:
- Stdout logging unchanged
- Additional handlers work seamlessly
- No blocking of request processing
- Clean integration with structlog

---

### Task 5.2: Google Cloud Logging Integration
**Status**: pending
**Files to modify**:
- Create: `src/core/gcp_logging.py` (following flat structure)
- `src/core/config.py` (extend ObservabilityConfig)
- `src/core/log_handlers.py` (add GCPHandler)

**Current State**:
- GCP Cloud Trace already integrated via OpenTelemetry
- `ObservabilityConfig` has GCP project ID and settings
- Authentication likely via default credentials (Cloud Run)

**Functional Requirements**:
1. Extend `ObservabilityConfig` with Cloud Logging settings:
   ```python
   enable_cloud_logging: bool = Field(default=False, description="Enable GCP Cloud Logging")
   cloud_logging_buffer_size: int = Field(default=100, gt=0, description="Batch size for log entries")
   cloud_logging_flush_interval: float = Field(default=5.0, gt=0, description="Flush interval in seconds")
   ```

2. Create `GCPLoggingHandler` in `log_handlers.py`:
   - Uses `google-cloud-logging` client library
   - Inherits from `BufferedHandler` for batching
   - Reuses `gcp_project_id` from ObservabilityConfig
   - Maps structlog levels to Cloud Logging severity

3. Integrate with existing observability:
   - Automatically link logs to traces using correlation ID
   - Add trace ID from current span to log entries
   - Use same resource labels as Cloud Trace
   - Support structured payload with existing JSON format

4. Enhanced correlation features:
   ```python
   # In log entry
   {
       "trace": f"projects/{project_id}/traces/{trace_id}",
       "spanId": span_id,
       "traceSampled": is_sampled
   }
   ```

**Implementation Notes**:
- Reuse existing GCP project configuration
- Default credentials work in Cloud Run
- Add `google-cloud-logging` to optional dependencies
- Preserve existing stdout logging (Cloud Logging is additional)
- Use existing `correlation_id` as `labels.correlation_id`

**Testing Approach**:
- Mock `google.cloud.logging.Client`
- Test batch accumulation and flushing
- Test level mapping accuracy
- Test trace correlation
- Verify graceful degradation if disabled

**Acceptance Criteria**:
- Logs appear in Cloud Logging Console
- Trace correlation visible in UI
- Structured JSON payload preserved
- No impact when disabled
- Batching reduces API calls

---

### Task 5.3: OpenTelemetry Logs Integration
**Status**: pending
**Files to modify**:
- `src/core/observability.py` (extend with logs support)
- `src/core/log_handlers.py` (add OTLPHandler)
- `pyproject.toml` (add opentelemetry-sdk-logs dependency)

**Current State**:
- OpenTelemetry tracing already configured
- Using Cloud Trace exporter for spans
- Custom `ErrorTrackingSpanProcessor` exists
- No OpenTelemetry logs integration yet

**Functional Requirements**:
1. Extend `setup_tracing()` to include logs setup:
   ```python
   def setup_observability() -> None:  # Rename from setup_tracing
       # Existing trace setup...
       if obs_config.enable_otlp_logs:
           setup_otel_logging()
   ```

2. Create `OTLPLogHandler` in `log_handlers.py`:
   - Uses OpenTelemetry Logs API
   - Inherits trace context automatically
   - Maps structlog fields to OTLP attributes
   - Supports both OTLP/gRPC and OTLP/HTTP

3. Add OTLP configuration to `ObservabilityConfig`:
   ```python
   enable_otlp_logs: bool = Field(default=False, description="Enable OTLP log export")
   otlp_endpoint: str | None = Field(default=None, description="OTLP collector endpoint")
   otlp_protocol: Literal["grpc", "http"] = Field(default="grpc", description="OTLP protocol")
   otlp_headers: dict[str, str] = Field(default_factory=dict, description="OTLP headers")
   ```

4. Correlation features:
   - Automatic trace context injection
   - Span ID and trace ID from current span
   - Resource attributes shared with traces
   - Consistent service naming

**Implementation Notes**:
- Leverage existing OpenTelemetry setup
- Share resource definition with traces
- Use same sampling decision as traces
- Support vendor-neutral OTLP protocol
- Can export to any OTLP collector (Grafana, Datadog, etc.)

**Testing Approach**:
- Test with OpenTelemetry Collector locally
- Verify trace-log correlation
- Test both gRPC and HTTP protocols
- Test batching and performance
- Mock OTLP endpoints

**Acceptance Criteria**:
- Logs correlated with traces in backends
- OTLP format compliance verified
- Works with standard collectors
- No performance regression
- Optional and disabled by default

---

### Task 5.4: Log Metrics and Health Monitoring
**Status**: pending
**Files to modify**:
- Create: `src/core/log_metrics.py`
- `src/core/log_handlers.py` (add MetricsHandler)
- `src/api/main.py` (add metrics endpoint)

**Current State**:
- No log metrics collection
- Health endpoint exists at `/health`
- No metrics exposition endpoint

**Functional Requirements**:
1. Create `LogMetricsCollector` in `log_metrics.py`:
   - Track log counts by level (error, warning, info)
   - Track error rates with sliding windows
   - Count unique error fingerprints
   - Monitor log throughput (logs/second)
   - Use efficient circular buffers for windows

2. Create `MetricsHandler` in `log_handlers.py`:
   - Updates LogMetricsCollector on each log
   - Extracts error fingerprints from TributumError
   - Non-blocking metric updates
   - Minimal overhead (<0.1ms)

3. Create `/metrics` endpoint for monitoring:
   ```python
   {
       "logs": {
           "total": 12345,
           "by_level": {"ERROR": 10, "WARNING": 100, ...},
           "rate_per_minute": 200,
           "errors_last_5min": 5
       },
       "errors": {
           "unique_fingerprints": 15,
           "top_errors": [...]
       }
   }
   ```

4. Add configuration to `LogConfig`:
   ```python
   enable_log_metrics: bool = Field(default=True, description="Collect log metrics")
   metrics_window_seconds: int = Field(default=300, gt=0, description="Metrics window size")
   ```

**Implementation Notes**:
- Use thread-safe counters (asyncio-safe)
- Bounded memory usage with circular buffers
- Compatible with Prometheus format (future)
- No external dependencies for core metrics
- Integrate with existing health checks

**Testing Approach**:
- Test metric accuracy
- Test sliding window calculations
- Test memory bounds
- Test endpoint responses
- Benchmark performance impact

**Acceptance Criteria**:
- Metrics available at `/metrics`
- Accurate counting and rates
- Memory usage bounded
- <0.1ms overhead per log
- Useful for monitoring dashboards

---

## Implementation Summary

### Key Design Decisions
1. **No nested directories** - Keep flat structure in `src/core/`
2. **Additive handlers** - Stdout always remains, handlers are additional
3. **Reuse existing config** - Extend ObservabilityConfig, don't duplicate
4. **Build on OpenTelemetry** - Leverage existing trace infrastructure
5. **Container-first** - Maintain stdout for Cloud Run compatibility

### Dependencies and Order
1. **Task 5.1** creates the handler abstraction (required by all others)
2. **Tasks 5.2, 5.3, 5.4** can be done in parallel after 5.1
3. Each handler is independent and optional

### Testing Strategy
- Mock all external services (GCP, OTLP)
- Test handler isolation (one failure doesn't affect others)
- Integration tests with real collectors where possible
- Performance benchmarks for each handler

### Success Metrics
- Zero impact on existing logging
- Each integration is optional and configurable
- Handlers don't block request processing
- Clean correlation between logs and traces
- Useful metrics for operational monitoring
