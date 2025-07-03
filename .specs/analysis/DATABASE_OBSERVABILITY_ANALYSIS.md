# Database Observability Implementation Analysis

## Executive Summary

This document analyzes the current state of database observability in the Tributum application and determines what minimal implementation is needed for comprehensive monitoring in GCP Cloud Run/GKE. The key insight: **GCP provides extensive automatic metrics collection - your application should emit structured logs and traces, while GCP handles aggregation and metrics computation**. Only specific gaps need implementation.

## Current State Analysis

### What's Already in Place

1. **OpenTelemetry Infrastructure**
   - `SQLAlchemyInstrumentor` is already configured in `src/core/observability.py`
   - Automatic tracing of database operations with correlation IDs
   - Support for GCP Cloud Trace, AWS X-Ray, and generic OTLP exporters
   - Trace sampling configuration for production environments
   - Custom `LoguruSpanExporter` for development environment

2. **Sophisticated SQL Query Logging**
   - Configuration flags: `enable_sql_logging` and `slow_query_threshold_ms` in `LogConfig`
   - Event listeners for `before_cursor_execute` and `after_cursor_execute` in `session.py`
   - Slow query detection and logging with duration tracking
   - Parameter sanitization for security (via `sanitize_sql_params` in `error_context.py`)
   - WeakKeyDictionary pattern for tracking query start times

3. **Async-First Database Layer**
   - Uses `postgresql+asyncpg://` driver exclusively
   - `_DatabaseManager` singleton pattern for engine lifecycle
   - Async session factory with proper cleanup
   - Connection pool configuration with asyncpg-specific settings

4. **Structured Logging with Loguru**
   - Exclusive use of Loguru (no standard logging)
   - Cloud-specific formatters (GCP, AWS) with proper field mapping
   - Correlation ID propagation via `RequestContext`
   - Context-aware logging with `.bind()` and `.contextualize()`

5. **Connection Pool Configuration**
   - Configurable pool settings: `pool_size`, `max_overflow`, `pool_timeout`
   - Pool pre-ping for connection health checking
   - Connection recycling every hour (`pool_recycle=3600`)
   - AsyncEngine with proper asyncpg connection arguments

## What GCP Provides Automatically

### Infrastructure Metrics (Cloud Run/GKE)

- **CPU & Memory**: Utilization, limits, throttling
- **Request Metrics**: Count, latency (p50, p95, p99), error rates
- **Instance Metrics**: Active instances, cold starts, scaling events
- **Network I/O**: Bytes in/out, connection count
- **Resource Consumption**: Correlated with application events

### From Your OpenTelemetry Implementation

- **Query Latency**: Automatically traced via `SQLAlchemyInstrumentor`
- **Service Dependencies**: Database calls mapped to endpoints
- **Error Traces**: Full stack traces with correlation IDs
- **Distributed Tracing**: Request flow across services

### From Your Structured Logs

- **Custom Metrics**: Any field in jsonPayload can become a metric
- **Error Aggregation**: Group by error_type, correlation_id
- **Performance Trends**: Compute percentiles from duration_ms fields

## Gap Analysis - What Actually Needs Implementation

### 1. SQL Query Visibility

**Current State:**

- ✅ Raw SQL logging with duration
- ✅ Slow query detection
- ✅ Parameter sanitization
- ✅ OpenTelemetry tracing
- ❌ Number of rows affected not logged

**Minimal Implementation Needed:**

```python
# Add 1 line to existing _after_cursor_execute
rows_affected = getattr(_cursor, 'rowcount', -1)
# Include in existing slow query log
```

**What GCP Can Derive:**

- Query frequency: COUNT by query_hash
- Slow query patterns: GROUP BY query_hash WHERE duration > threshold
- Query performance trends: Percentiles over time windows
- Resource correlation: JOIN with CPU/memory metrics by timestamp

### 2. Connection Pool Health

**Current State:**

- ✅ Pool configuration (size, timeout, pre-ping)
- ✅ Connection recycling
- ❌ Pool state not exposed in logs

**Minimal Implementation Needed:**

```python
# Add to health endpoint (5 lines)
pool = engine.pool
logger.bind(
    metric_type="db.pool.health",
    checked_out=pool.checkedout(),
    size=pool.size()
).info("Pool health")
```

**What GCP Can Derive:**

- Pool exhaustion events: WHERE checked_out >= size
- Connection leak detection: Trending checked_out over time
- Optimal pool size: Correlation with request latency

### 3. Transaction Monitoring

**Current State:**

- ✅ Commit/rollback in session context manager
- ❌ Transaction events not explicitly logged

**Minimal Implementation Needed:**

- Your existing session cleanup logs commits/rollbacks
- Just ensure correlation_id is included

**What GCP Can Derive:**

- Rollback rate: COUNT(rollback) / COUNT(commit + rollback)
- Transaction duration: From begin/commit timestamps
- Problematic endpoints: GROUP BY path WHERE rollback rate > threshold

### 4. What You DON'T Need to Implement

❌ **Query Statistics Collector**

- GCP BigQuery can aggregate query patterns from logs
- No need for in-memory LRU cache

❌ **Resource Monitoring**

- Cloud Run/GKE provides CPU/memory metrics
- Automatic correlation with your logs via timestamp

❌ **Metric Aggregation**

- Use log-based metrics instead of in-app computation
- GCP handles percentiles, rates, and time windows

❌ **Complex Pool Monitoring**

- Event listeners for every checkout/checkin are overkill
- Periodic health check logging is sufficient

## Minimal Implementation Required

### Phase 1: Add Row Count to Slow Query Logs (1 line change)

```python
# In existing _after_cursor_execute in src/infrastructure/database/session.py

def _after_cursor_execute(
    _conn: Connection,
    _cursor: DBAPICursor,
    statement: str,
    parameters: dict[str, Any] | list[Any] | tuple[Any, ...] | None,
    context: ExecutionContext,
    executemany: bool,
) -> None:
    """Log slow queries and track query metrics."""
    settings = get_settings()

    # Existing duration calculation...
    duration_ms = 0.0
    start_time = _query_start_times.get(context)
    if start_time is not None:
        duration_ms = (time.time() - start_time) * 1000
        _query_start_times.pop(context, None)

    # ADD THIS LINE:
    rows_affected = getattr(_cursor, 'rowcount', -1)

    correlation_id = RequestContext.get_correlation_id()

    # Existing slow query logging - just add rows_affected
    if (
        settings.log_config.enable_sql_logging
        and duration_ms >= settings.log_config.slow_query_threshold_ms
    ):
        sanitized_params = sanitize_sql_params(parameters)
        clean_statement = " ".join(statement.split())[:500]

        logger.warning(
            "Slow query detected: {}... Duration: {:.2f}ms Rows: {}",
            clean_statement[:100],
            round(duration_ms, 2),
            rows_affected,  # ADD THIS
            query=clean_statement,
            duration_ms=round(duration_ms, 2),
            rows_affected=rows_affected,  # ADD THIS FIELD
            parameters=sanitized_params,
            correlation_id=correlation_id,
            executemany=executemany,
            threshold_ms=settings.log_config.slow_query_threshold_ms,
        )
```

### Phase 2: Add Pool Metrics to Health Check (5 lines)

```python
# In existing health endpoint in src/api/main.py

@application.get("/health")
async def health() -> dict[str, object]:
    """Health check endpoint with enhanced metrics."""
    health_status: dict[str, object] = {"status": "healthy", "database": False}

    is_healthy, error_msg = await check_database_connection()
    health_status["database"] = is_healthy

    # ADD THESE LINES:
    if is_healthy:
        engine = get_engine()
        pool = engine.pool
        logger.bind(
            metric_type="db.pool.health",
            checked_out=pool.checkedout(),
            size=pool.size(),
            overflow=pool.overflow()
        ).info("Database pool health check")

    if not is_healthy:
        logger.warning("Database health check failed: {}", error_msg)
        health_status["status"] = "degraded"

    return health_status
```

### Phase 3: Ensure Transaction Logging (might already exist)

```python
# Check if your get_async_session already logs commits/rollbacks
# If not, add these minimal logs:

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session with automatic cleanup."""
    async_session_factory = get_session_factory()
    async with async_session_factory() as session:
        correlation_id = RequestContext.get_correlation_id()
        try:
            yield session
            await session.commit()
            # ADD IF MISSING:
            logger.bind(
                correlation_id=correlation_id,
                event_type="transaction.commit"
            ).debug("Transaction committed")
        except Exception:
            await session.rollback()
            # ADD IF MISSING:
            logger.bind(
                correlation_id=correlation_id,
                event_type="transaction.rollback"
            ).warning("Transaction rolled back")
            raise
        finally:
            await session.close()
```

That's it! Just 3 minimal changes:

1. Add `rows_affected` to slow query logs
2. Log pool state in health check
3. Ensure transaction commits/rollbacks are logged

## What You DON'T Need to Implement

❌ **Query Statistics Collector** - Let GCP aggregate from logs
❌ **Pool Event Listeners** - Health check snapshots are sufficient
❌ **Transaction Timing** - GCP can calculate from commit/rollback timestamps
❌ **In-Memory Metrics** - GCP handles all aggregation
❌ **EXPLAIN ANALYZE** - Only if you need deep query optimization

## GCP Configuration (No Code Changes Required)

Configure these log-based metrics in GCP Console:

```yaml
# Create these metrics in GCP Console or via Terraform
logBasedMetrics:
  - name: slow_database_queries
    description: "Count of slow database queries"
    filter: |
      resource.type="cloud_run_revision"
      jsonPayload.message="Slow query detected"
      jsonPayload.duration_ms > 1000
    metricDescriptor:
      metricKind: DELTA
      valueType: INT64

  - name: database_pool_active_connections
    description: "Active database connections"
    filter: |
      resource.type="cloud_run_revision"
      jsonPayload.metric_type="db.pool.health"
    metricDescriptor:
      metricKind: GAUGE
      valueType: INT64
    valueExtractor: "EXTRACT(jsonPayload.checked_out)"

  - name: transaction_rollbacks
    description: "Database transaction rollbacks"
    filter: |
      resource.type="cloud_run_revision"
      jsonPayload.event_type="transaction.rollback"
    metricDescriptor:
      metricKind: DELTA
      valueType: INT64
```

## Cloud-Native Monitoring Philosophy

**Key Principle**: Your application emits events, GCP computes metrics.

### Why This Approach?

1. **Separation of Concerns**
   - Application: Emit structured events with context
   - GCP: Aggregate, compute percentiles, detect anomalies

2. **No Memory Overhead**
   - No in-app metric storage
   - No statistical computations
   - Minimal performance impact

3. **Flexible Analysis**
   - Change metrics without code deployment
   - Ad-hoc queries on historical data
   - Correlation with infrastructure metrics

4. **Cost Effective**
   - Use GCP's built-in capabilities
   - No additional dependencies
   - Scales automatically

## Testing Requirements

Following the codebase's patterns:

1. **Unit Tests (100% coverage required)**

```python
# tests/unit/infrastructure/database/test_session_monitoring.py
import pytest
from pytest_mock import MockerFixture  # Never unittest.mock

async def test_query_stats_collector():
    """Test query statistics collection."""
    collector = QueryStatsCollector(max_queries=2)

    # Test LRU eviction
    collector.record_query("SELECT 1", 100.0, False)
    collector.record_query("SELECT 2", 2000.0, True)
    collector.record_query("SELECT 3", 50.0, False)  # Should evict SELECT 1

    stats = collector._stats
    assert "SELECT 1" not in [s.query_hash for s in stats.values()]

async def test_pool_health_metrics(mocker: MockerFixture):
    """Test connection pool health reporting."""
    mock_pool = mocker.Mock()
    mock_pool.size.return_value = 10
    mock_pool.checkedout.return_value = 3
    # ... test pool metrics
```

1. **Integration Tests**

```python
# tests/integration/database/test_observability.py
@pytest.mark.integration
async def test_slow_query_logging(db_session, caplog):
    """Test that slow queries are logged with metrics."""
    # Execute a query with pg_sleep to ensure it's slow
    await db_session.execute(text("SELECT pg_sleep(0.2)"))

    # Verify log output contains expected fields
    assert "Slow query detected" in caplog.text
    assert "rows_affected" in caplog.text
```

1. **Parallel Test Support**
   - Tests use worker-specific databases
   - No shared state between test workers
   - Fixtures handle proper cleanup

## Security Considerations

1. **Parameter Sanitization**
   - Already implemented in `sanitize_sql_params`
   - Ensure no sensitive data in metrics

2. **Query Plan Exposure**
   - Only enable EXPLAIN in development
   - Sanitize table names if needed

3. **Metric Cardinality**
   - Limit unique query hashes tracked
   - Aggregate similar queries

## Implementation Timeline

**Total effort: 2-3 hours**

1. **Code Changes (30 minutes)**
   - Add rows_affected to slow query logs
   - Add pool metrics to health endpoint
   - Verify transaction logging exists

2. **GCP Configuration (1 hour)**
   - Create log-based metrics in Console
   - Set up alerting policies
   - Create monitoring dashboard

3. **Testing (1 hour)**
   - Unit tests for new fields
   - Integration test with real database
   - Verify GCP metric collection

## Monitoring Queries

Example queries for GCP Cloud Logging (BigQuery syntax):

```sql
-- Find repeatedly slow queries with correlation
SELECT
  jsonPayload.query_hash,
  COUNT(*) as executions,
  AVG(CAST(jsonPayload.duration_ms as FLOAT64)) as avg_duration_ms,
  MAX(CAST(jsonPayload.duration_ms as FLOAT64)) as max_duration_ms,
  COUNT(DISTINCT jsonPayload.correlation_id) as unique_requests,
  ARRAY_AGG(DISTINCT jsonPayload.correlation_id LIMIT 5) as sample_correlation_ids
FROM `project.logs.cloud_run_logs`
WHERE
  jsonPayload.message = "Slow query detected"
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY jsonPayload.query_hash
HAVING COUNT(*) > 5
ORDER BY avg_duration_ms DESC

-- Connection pool health over time
SELECT
  TIMESTAMP_TRUNC(timestamp, MINUTE) as minute,
  AVG(CAST(jsonPayload.checked_out as INT64)) as avg_active,
  MAX(CAST(jsonPayload.checked_out as INT64)) as max_active,
  AVG(CAST(jsonPayload.size as INT64)) as pool_size
FROM `project.logs.cloud_run_logs`
WHERE jsonPayload.metric_type = "db.pool.health"
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY minute
ORDER BY minute DESC

-- Transaction rollback analysis
SELECT
  DATE(timestamp) as date,
  COUNT(CASE WHEN jsonPayload.event_type = "transaction.commit" THEN 1 END) as commits,
  COUNT(CASE WHEN jsonPayload.event_type = "transaction.rollback" THEN 1 END) as rollbacks,
  AVG(CASE WHEN jsonPayload.event_type = "transaction.commit"
      THEN CAST(jsonPayload.duration_ms as FLOAT64) END) as avg_commit_ms,
  AVG(CASE WHEN jsonPayload.event_type = "transaction.rollback"
      THEN CAST(jsonPayload.duration_ms as FLOAT64) END) as avg_rollback_ms
FROM `project.logs.cloud_run_logs`
WHERE jsonPayload.event_type IN ("transaction.commit", "transaction.rollback")
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC
```

## Conclusion

Your existing observability foundation (OpenTelemetry + structured logging) already provides 90% of what's needed. The minimal implementation required:

### What to Implement (30 minutes)

1. **Add `rows_affected` to slow query logs** (1 line)
2. **Log pool metrics in health endpoint** (5 lines)
3. **Ensure transaction events are logged** (may already exist)

### What GCP Handles Automatically

- **Infrastructure metrics**: CPU, memory, network, instances
- **Query performance**: Aggregation, percentiles, patterns
- **Resource correlation**: Linking high CPU to slow queries
- **Historical analysis**: Trends, anomalies, forecasting

### Why This Approach Works

- **Cloud-native**: Let the platform do the heavy lifting
- **Maintainable**: Minimal code, maximum insight
- **Scalable**: No memory overhead in your application
- **Flexible**: Change metrics without deploying code

The key insight: **In cloud environments, your application should emit structured events, not compute metrics.** GCP's log-based metrics, combined with automatic infrastructure monitoring, provide comprehensive observability without the complexity of traditional APM solutions.
