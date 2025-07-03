# Error Handling, Logging & Observability Analysis

## Executive Summary

The Tributum application has a well-structured error handling and observability framework with strong foundations. However, deep analysis reveals a **CRITICAL SECURITY ISSUE** where sensitive error context is exposed to clients without sanitization. Additionally, several enhancements are needed to fully meet the requirements and leverage GCP's observability infrastructure.

## ⚠️ CRITICAL SECURITY ISSUE

**Sensitive data in error responses is NOT sanitized!**

While the error context is properly sanitized for logging (passwords become "[REDACTED]"), the raw unsanitized context is returned to clients in the API response. This occurs in `src/api/middleware/error_handler.py:102-103`:

```python
details = exc.context if exc.context else None  # Raw context, not sanitized!
```

This must be fixed immediately before any production deployment.

## Current Capabilities vs Requirements

### 1. Complete Stack Traces with Exact Line Numbers ✅ (Fully Implemented)

**Current Implementation:**

- `TributumError.stack_trace` captures full stack traces using `traceback.format_stack()`
- Stack frames stored with complete details (file, line, function, code)
- Error fingerprinting uses stack frames to identify exact error location
- Stack traces are:
  - **Logged**: Full stack trace included in sanitized error context
  - **Returned to client**: Only in development mode via `debug_info.stack_trace`
  - **Hidden in production**: `debug_info` is null in production responses

**GCP Integration Status:**

- GCPFormatter includes basic exception info (`exc_info`) but not the custom stack trace
- The `@type` field for GCP Error Reporting is missing
- Stack traces need restructuring for optimal GCP Error Reporting grouping

**Required Modifications:**

```python
# In src/core/logging.py - enhance GCP formatter for Error Reporting
if record.get("exception") or "stack_trace" in extra:
    # Add Error Reporting specific fields
    structured["@type"] = "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"
    structured["context"] = {
        "reportLocation": {
            "filePath": record.get("pathname"),
            "lineNumber": record.get("lineno"),
            "functionName": record.get("funcName")
        }
    }
    # Include the full custom stack trace
    if "stack_trace" in extra:
        structured["stack_trace"] = extra["stack_trace"]
```

### 2. Full Context Capture ⚠️ (Partial with Security Issues)

**Current Implementation:**

- ✅ Request parameters logged by RequestLoggingMiddleware (method, path, client IP, duration)
- ✅ Correlation IDs propagated via contextvars
- ✅ Custom context dictionary in TributumError (but exposed unsanitized!)
- ✅ Request metadata available in error handlers
- ❌ No authentication/user system exists (no user context to capture)
- ❌ No application state snapshots
- ⚠️ Context is sanitized for logging but NOT for API responses

**What Gets Captured in Errors:**

```python
# From error_handler.py - what's actually logged
error_context = {
    "error_type": type(exc).__name__,
    "error_code": exc.error_code.value,
    "message": str(exc),
    "fingerprint": exc.fingerprint,
    "severity": exc.severity.value,
    "context": exc.context,  # This gets sanitized for logging
    "stack_trace": exc.stack_trace,
    "cause": str(exc.__cause__) if exc.__cause__ else None,
}
```

**Required Modifications:**

1. **Fix Security Issue - Sanitize Error Details:**

```python
# In src/api/middleware/error_handler.py
from src.core.error_context import sanitize_error_context

# Replace line 102-103
details = sanitize_error_context(exc.context) if exc.context else None
```

1. **Add Application State Context:**

```python
# In src/core/context.py - add application state tracking
import psutil
from sqlalchemy.pool import Pool

class ApplicationContext:
    """Tracks application state for error context."""

    @staticmethod
    def get_state() -> dict[str, Any]:
        process = psutil.Process()
        return {
            "memory": {
                "rss_mb": process.memory_info().rss / 1024 / 1024,
                "percent": process.memory_percent()
            },
            "cpu_percent": process.cpu_percent(interval=0.1),
            "open_files": len(process.open_files()),
            "num_threads": process.num_threads(),
            "connections": {
                # Add database pool stats if available
                "db_pool_size": getattr(Pool, 'size', lambda: 0)(),
                "db_pool_checked_out": getattr(Pool, 'checked_out', lambda: 0)()
            }
        }

# Update error handlers to include app state
error_context["app_state"] = ApplicationContext.get_state()
```

1. **Future: User Context (when authentication is added):**

```python
# When authentication is implemented, add to RequestContextMiddleware
if hasattr(request.state, "user"):
    context.set("user_id", request.state.user.id)
    context.set("user_role", request.state.user.role)
```

### 3. Error Frequency and Pattern Tracking ✅ (GCP Handles This!)

**Current Implementation:**

- ✅ Error fingerprinting for grouping (`TributumError.error_fingerprint()`)
- ✅ Structured logging with all error details
- ✅ All errors logged with severity, type, fingerprint, and context
- ✅ Request logging middleware tracks endpoint performance

**What GCP Provides Automatically:**

1. **Cloud Logging Aggregation** (No code needed!):
   - Automatic log ingestion from stdout/stderr
   - Log-based metrics creation via Cloud Console
   - Error grouping by fingerprint field
   - Query capabilities: `jsonPayload.fingerprint="abc123"`

2. **Error Reporting** (Automatic for Cloud Run/GKE):
   - Groups errors by stack trace similarity
   - Tracks error rates and new vs recurring errors
   - Provides error trends and notifications
   - Works with your existing error logging!

3. **Cloud Monitoring Metrics** (From logs, no code needed):

   ```yaml
   # Example log-based metric (created in Cloud Console)
   Name: error_rate_by_severity
   Filter: severity>=ERROR
   Labels:
     - jsonPayload.severity
     - jsonPayload.error_code
     - resource.service_name
   ```

**What You DON'T Need to Implement:**

- ❌ Custom metrics collection for errors (GCP derives from logs)
- ❌ Error counters (Cloud Logging counts for you)
- ❌ Aggregation logic (Cloud Monitoring handles this)
- ❌ Additional OpenTelemetry Metrics for basic error tracking

**What You MIGHT Want (Optional):**

- Custom business metrics (e.g., payment failures, not generic errors)
- Performance histograms for specific operations
- Real-time metrics (if log-based metrics' 1-minute delay is too slow)

### 4. Distinguish Expected vs Unexpected Errors ⚠️ (Implicit Only)

**Current Implementation:**

- ✅ Severity levels: LOW, MEDIUM, HIGH, CRITICAL (in `ErrorSeverity` enum)
- ✅ Exception hierarchy implies expectedness:
  - `ValidationError` (LOW) - implicitly expected
  - `NotFoundError` (LOW) - implicitly expected
  - `BusinessRuleError` (MEDIUM) - implicitly expected
  - `UnauthorizedError` (HIGH) - security concern
- ❌ No explicit `is_expected` attribute
- ❌ Same logging level (ERROR) for all error types

**How Errors Are Currently Differentiated:**

- By HTTP status code mapping (400s vs 500s)
- By severity level (LOW/MEDIUM vs HIGH/CRITICAL)
- By exception type in error fingerprinting

**Required Modifications:**

1. **Add explicit expected/unexpected classification:**

```python
# In src/core/exceptions.py - add to TributumError
class TributumError(Exception):
    """Base exception with existing fields..."""

    @property
    def is_expected(self) -> bool:
        """Determine if this is an expected error based on severity."""
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)

    @property
    def should_alert(self) -> bool:
        """Determine if this error should trigger alerts."""
        return self.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL)
```

1. **Differentiate logging levels in error handlers:**

```python
# In src/api/middleware/error_handler.py
async def tributum_error_handler(request: Request, exc: TributumError) -> JSONResponse:
    """Handle TributumError with appropriate logging level."""
    correlation_id = get_correlation_id()

    # Create sanitized context for logging
    error_context = {...}  # existing code

    # Log based on error expectedness
    if exc.is_expected:
        logger.warning(  # Use WARNING for expected errors
            f"{exc.error_code.value}: {exc.message}",
            **error_context,
            extra={"alert": False}
        )
    else:
        logger.error(  # Use ERROR for unexpected errors
            f"{exc.error_code.value}: {exc.message}",
            **error_context,
            extra={"alert": True, "notify_oncall": exc.severity == ErrorSeverity.CRITICAL}
        )

    # Rest of handler...
```

1. **Update generic exception handler for unexpected errors:**

```python
# In generic_exception_handler - these are always unexpected
logger.error(
    f"Unhandled exception: {type(exc).__name__}",
    **error_context,
    extra={
        "alert": True,
        "is_expected": False,
        "error_category": "system_error"
    }
)
```

1. **For GCP Cloud Monitoring alerts:**

```python
# Alert policy would use log-based metrics:
# - Filter: jsonPayload.extra.alert=true
# - Threshold: Rate > X errors/minute
# - Notification: Based on severity
```

## GCP Cloud Run/GKE Integration Strategy

### 1. **Resource Monitoring** ✅ (GCP Provides This!)

**What Cloud Run/GKE Automatically Provides:**

- **CPU & Memory Metrics**: Real-time resource usage per container
- **Request Metrics**: Latency, request count, error rates
- **Container Metrics**: Startup time, instance count, concurrency
- **Network Metrics**: Ingress/egress, request sizes

**Access via:**

- Cloud Console → Monitoring → Metrics Explorer
- Pre-built dashboards for Cloud Run/GKE
- No application code needed!

### 2. **Enhance GCP Error Reporting Integration**

**Current State:**

- Errors are logged with stack traces and fingerprints
- GCP Error Reporting will auto-detect errors from logs
- Missing optimal formatting for better grouping

**Minimal Enhancement Required:**

```python
# In src/core/logging.py - add Error Reporting hints
def _format_for_gcp(self, record: LogRecord) -> dict[str, Any]:
    """Enhanced GCP formatter with Error Reporting support."""
    # Existing code...

    # Help Error Reporting group errors better
    if record["level"].name in ["ERROR", "CRITICAL"]:
        # Add service context for better filtering
        structured["serviceContext"] = {
            "service": self.app_name,
            "version": self.app_version,
        }

        # If we have a fingerprint, add it as a label for grouping
        if "fingerprint" in extra:
            structured["labels"]["error_fingerprint"] = extra["fingerprint"][:8]

    return structured
```

### 3. **Leverage Existing OpenTelemetry Tracing**

**Current State:**

- ✅ OpenTelemetry tracing with GCP Cloud Trace exporter
- ✅ Auto-instrumentation for FastAPI and SQLAlchemy
- ✅ Correlation IDs link logs and traces

**Simple Enhancement for Error Context:**

```python
# In src/api/middleware/error_handler.py - add to existing handlers
span = trace.get_current_span()
if span.is_recording():
    span.set_status(StatusCode.ERROR, str(exc))
    span.record_exception(exc)  # This links errors to traces!
```

### 4. **What You DON'T Need to Implement**

**GCP Handles These Automatically:**

1. **Basic Metrics**:
   - Request rates, error rates, latencies
   - Resource utilization (CPU, memory, disk)
   - Network I/O and bandwidth

2. **Log-Based Metrics**:
   - Create custom metrics from log entries
   - No need for app-level counters
   - 1-minute aggregation granularity

3. **Alerting**:
   - Alert policies based on logs or metrics
   - Integration with PagerDuty, Slack, etc.
   - SLO monitoring and error budgets

### 5. **Development Environment Observability**

**Minimal Local Stack (matches production behavior):**

```yaml
# docker-compose.observability.yml
version: '3.8'
services:
  jaeger:
    image: jaegertracing/all-in-one:1.56
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
```

**Development `.env`:**

```bash
# Traces go to local Jaeger
OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://localhost:4317

# Logs to console with full context
LOG_CONFIG__LOG_FORMATTER_TYPE=console
LOG_CONFIG__LOG_LEVEL=DEBUG
```

## Implementation Priority (Revised Based on GCP Capabilities)

### 🚨 CRITICAL - Immediate Fix Required

1. **Fix Security Vulnerability** (Before ANY production deployment):

   ```python
   # In src/api/middleware/error_handler.py line 102-103
   # Replace: details = exc.context if exc.context else None
   # With:    details = sanitize_error_context(exc.context) if exc.context else None
   ```

### Phase 1: Essential Enhancements Only (1-2 days)

1. **Optimize for GCP Error Reporting**
   - Add `serviceContext` to GCPFormatter for better filtering
   - Add error fingerprint to labels for custom grouping
   - Link errors to traces via `span.record_exception()`

2. **Implement Expected vs Unexpected Classification**
   - Add `is_expected` property to `TributumError`
   - Use WARNING for expected, ERROR for unexpected
   - Add `alert` field for log-based alerting

3. **Add Application State Context** (Optional but useful)
   - Memory/CPU stats using psutil for debugging
   - Database pool stats for connection issues
   - Only for HIGH/CRITICAL severity errors

### Phase 2: GCP Configuration (No Code!)

1. **Create Log-Based Metrics in Cloud Console**
   - Error rate by severity: `severity>=ERROR`
   - Error rate by endpoint: `jsonPayload.endpoint`
   - Business errors: `jsonPayload.error_code="BUSINESS_RULE_VIOLATION"`

2. **Set Up Alert Policies**
   - High severity errors: `jsonPayload.extra.alert=true`
   - Error rate thresholds
   - New error types (using fingerprints)

3. **Configure Dashboards**
   - Use built-in Cloud Run/GKE dashboards
   - Add custom charts for log-based metrics
   - Link traces to errors via correlation IDs

### What NOT to Implement (GCP Handles It)

❌ **Custom Metrics Collection**: GCP derives from logs
❌ **Resource Monitoring**: Cloud Run/GKE provides automatically
❌ **Error Aggregation**: Cloud Logging/Error Reporting handles it
❌ **Performance Metrics**: Already in Cloud Run/GKE dashboards
❌ **Prometheus/Grafana**: Redundant with Cloud Monitoring

## Testing Requirements

### Unit Tests for Security Fix

```python
# tests/unit/api/middleware/test_error_handler_security.py
async def test_error_context_sanitization():
    """Ensure sensitive data is sanitized in error responses."""
    error = ValidationError(
        message="Invalid input",
        context={"password": "secret123", "api_key": "sk-12345"}
    )

    response = await tributum_error_handler(mock_request, error)
    response_data = response.body.decode()

    assert "secret123" not in response_data
    assert "[REDACTED]" in response_data
```

### Integration Tests for Observability

```python
# tests/integration/test_error_observability.py
async def test_error_trace_correlation():
    """Verify errors are properly correlated with traces."""
    with trace_operation("test_operation") as span:
        # Trigger an error
        # Verify span status and attributes

async def test_error_metrics_recording():
    """Verify error metrics are recorded correctly."""
    # Generate known errors
    # Check metric values
```

## GCP-Specific Configuration

### Cloud Run Environment Variables

```bash
# Automatically detected by the app
K_SERVICE=tributum-api
K_REVISION=tributum-api-00001-abc

# Manual configuration
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
LOG_CONFIG__LOG_LEVEL=WARNING  # Reduce noise in production
```

### GCP Alert Policies (Terraform/Console)

```hcl
# High severity errors
resource "google_monitoring_alert_policy" "high_severity_errors" {
  display_name = "High Severity Errors"
  conditions {
    display_name = "Error rate"
    condition_matched_log {
      filter = "jsonPayload.extra.alert=true AND severity>=ERROR"
    }
  }
}
```

## Conclusion

After deep analysis considering GCP's capabilities, the Tributum application needs minimal changes:

### What You Already Have ✅

1. **Complete Error Context**: Stack traces, fingerprints, request details
2. **Structured Logging**: Everything GCP needs for aggregation and metrics
3. **Distributed Tracing**: OpenTelemetry with correlation IDs
4. **Error Grouping**: Fingerprints enable automated pattern detection

### What Actually Needs Implementation 🔧

1. **CRITICAL**: Fix security vulnerability (unsanitized error context)
2. **Minor**: Add serviceContext and labels to GCPFormatter
3. **Minor**: Link errors to traces with span.record_exception()
4. **Nice-to-have**: Expected vs unexpected error classification

### What GCP Provides (No Code Needed!) 🎁

1. **Metrics**: Request rates, error rates, latencies, resource usage
2. **Aggregation**: Log-based metrics with custom labels
3. **Monitoring**: Pre-built dashboards for Cloud Run/GKE
4. **Alerting**: Policies based on logs, metrics, or SLOs
5. **Error Reporting**: Automatic grouping and trend analysis

### Key Insight 💡

Your current implementation already provides 90% of what's needed for production observability. GCP's platform handles aggregation, metrics, and monitoring automatically from your structured logs and traces. Focus on the security fix and minor enhancements rather than building redundant metrics collection.
