# Task 3: Security and Sensitive Data Filtering

## Overview
Enhance the logging system's security by extending the existing sanitization framework to cover more data types and provide configurable filtering strategies.

## Project Context

### Current Security Implementation
The project has a well-structured sanitization system:

1. **Error Context Sanitization** (`src/core/error_context.py`):
   - `SENSITIVE_FIELD_PATTERNS`: 20+ regex patterns for field names
   - `is_sensitive_field()`: Pattern matching function
   - `sanitize_context()`: Deep recursive sanitization with type preservation
   - `SENSITIVE_HEADERS`: Predefined list of headers to redact
   - Uses "[REDACTED]" as replacement value

2. **Request Logging** (`src/api/middleware/request_logging.py`):
   - `_sanitize_headers()`: Redacts sensitive HTTP headers
   - Integrates with `sanitize_context()` for query params and body
   - Separate handling for different content types

3. **Integration Points**:
   - Error handler uses `sanitize_context()` before logging
   - Request logger sanitizes all user input
   - ORJSONRenderer handles special types in `_process_dict()`

### Architecture Patterns
- Flat module structure in `src/core/` (no subdirectories)
- Sanitization happens at multiple layers (middleware, error handling, logging)
- Type preservation is important (sanitized data keeps original structure)
- Performance is critical (used in hot paths)

## Tasks

### Task 3.1: Enhanced Pattern-Based Detection
**Status**: pending
**Files to modify**:
- `src/core/error_context.py`
- `src/core/config.py` (add to LogConfig)

**Current State**:
- `SENSITIVE_FIELD_PATTERNS` uses field name matching only
- No content-based detection (e.g., credit card numbers in values)
- Patterns are hardcoded, not configurable

**Functional Requirements**:
1. Extend `error_context.py` with value-based detection:
   - Create `detect_sensitive_value(value: str) -> bool` function
   - Add patterns for common sensitive data formats:
     - Credit card: `r'\b(?:\d[ -]*?){13,19}\b'` with Luhn check
     - Email: `r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'`
     - Phone: `r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'`
     - UUID: `r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'`
     - JWT: `r'\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b'`
   - Compile patterns once for performance

2. Add configuration to LogConfig:
   - `additional_sensitive_patterns`: list[str] = Field(default_factory=list, description="Additional regex patterns")
   - `sensitive_value_detection`: bool = Field(default=True, description="Enable value-based detection")
   - `excluded_fields_from_sanitization`: list[str] = Field(default_factory=list, description="Fields to never sanitize")

3. Enhance `_sanitize_dict()` to:
   - Check values with `detect_sensitive_value()` when enabled
   - Skip fields in excluded_fields_from_sanitization
   - Use compiled regex patterns for performance
   - Handle string values only (skip other types)

**Implementation Notes**:
- Patterns should be compiled at module level or cached
- Luhn validation should be a separate function for credit cards
- Keep existing SENSITIVE_FIELD_PATTERNS as the primary method
- Value detection is secondary and more expensive

**Testing Approach**:
- Test each pattern with valid/invalid examples
- Test Luhn algorithm implementation
- Test performance with large dictionaries
- Test with configuration variations
- Ensure no regression in existing sanitization

**Acceptance Criteria**:
- Value-based detection works alongside field-name detection
- Performance impact < 3ms for typical payloads
- Configurable patterns load from environment
- No false positives on common non-sensitive patterns

---

### Task 3.2: Enhanced Sanitization Strategies
**Status**: pending
**Files to modify**:
- `src/core/error_context.py`
- `src/core/logging.py` (integrate with ORJSONRenderer)

**Current State**:
- `sanitize_context()` only supports full redaction with "[REDACTED]"
- Already handles nested dicts and lists recursively
- Uses deepcopy to preserve original data
- No circular reference protection

**Functional Requirements**:
1. Add sanitization strategies to `error_context.py`:
   - Create `SanitizationStrategy` enum: REDACT, MASK, HASH, TRUNCATE
   - Modify `_sanitize_dict()` to accept strategy parameter
   - Implement strategy functions:
     - `redact_value(value: Any) -> str` - returns "[REDACTED]"
     - `mask_value(value: str) -> str` - shows last 4 chars: "****1234"
     - `hash_value(value: str) -> str` - returns "sha256:abcd1234" (first 8 chars)
     - `truncate_value(value: str, max_length: int = 10) -> str` - "longval..."

2. Add circular reference protection:
   - Track visited objects using id() in a set
   - Return "[CIRCULAR]" when circular reference detected
   - Clear visited set after sanitization completes

3. Enhance integration with logging:
   - Update `ORJSONRenderer._process_dict()` to use sanitize_context
   - Add sanitization to `inject_logger_context` processor
   - Ensure sanitization happens before JSON serialization

4. Add field-specific strategy configuration:
   - Create mapping: `dict[str, SanitizationStrategy]` in config
   - Default strategy for unknown sensitive fields
   - Allow per-field strategy override

**Implementation Notes**:
- Keep `sanitize_context()` signature for backward compatibility
- Add new `sanitize_context_with_options()` for advanced usage
- Strategy functions should handle non-string types gracefully
- Hash should use hashlib.sha256 with consistent encoding

**Testing Approach**:
- Test each strategy with various input types
- Create circular reference test cases
- Test performance with deeply nested structures
- Verify integration with ORJSONRenderer
- Test strategy configuration

**Acceptance Criteria**:
- All strategies work correctly with type preservation
- Circular references don't cause infinite loops
- Performance impact < 5ms for typical payloads
- Backward compatibility maintained
- Strategies configurable via LogConfig

---

### Task 3.3: Sanitization Performance Optimization
**Status**: pending
**Files to modify**:
- `src/core/error_context.py`
- `src/api/middleware/request_logging.py`

**Current State**:
- `sanitize_context()` uses deepcopy on every call
- No caching of sanitization results
- Regex patterns compiled on every check
- Called multiple times in request pipeline

**Functional Requirements**:
1. Optimize pattern matching:
   - Pre-compile all regex patterns at module level
   - Create `_compiled_patterns` list at startup
   - Use `re.compile()` with re.IGNORECASE flag
   - Cache pattern matching results for repeated field names

2. Implement smart copying:
   - Only deepcopy when sensitive data is found
   - Return original dict if no sensitive data
   - Track if sanitization was needed via flag
   - Avoid copying immutable types

3. Add sanitization caching:
   - LRU cache for field name checks (size=1000)
   - Cache sanitization results for identical inputs
   - Use hash of dict structure as cache key
   - Clear cache on configuration reload

4. Optimize middleware integration:
   - Single sanitization pass in RequestLoggingMiddleware
   - Reuse sanitized results across log entries
   - Lazy sanitization only when actually logging

**Implementation Notes**:
- Use `functools.lru_cache` for caching
- Patterns should be module-level constants
- Consider memory vs speed tradeoffs
- Maintain thread safety with caching

**Testing Approach**:
- Benchmark before/after performance
- Test cache hit rates
- Verify no memory leaks from caching
- Test with various payload sizes
- Ensure correctness not compromised

**Acceptance Criteria**:
- 50%+ performance improvement in sanitization
- No increase in memory usage > 10MB
- Cache invalidation works correctly
- Thread-safe implementation
- No functional regressions

---

### Task 3.4: Security Monitoring and Compliance Helpers
**Status**: pending
**Files to modify**:
- `src/core/logging.py`
- `src/core/error_context.py`
- `src/api/schemas/errors.py` (enhance ErrorResponse)

**Current State**:
- No tracking of what data was sanitized
- No visibility into sanitization effectiveness
- No compliance metadata in logs
- Error responses don't indicate if data was sanitized

**Functional Requirements**:
1. Add sanitization metrics:
   - Create `SanitizationReport` class:
     - fields_sanitized: list[str]
     - values_sanitized: int
     - patterns_matched: dict[str, int]
     - sanitization_time_ms: float
   - Return report from `sanitize_context_with_options()`
   - Include report in debug logs when enabled

2. Enhance error responses for compliance:
   - Add `sanitization_applied: bool` to ErrorResponse
   - Add `data_classification: str | None` for sensitivity level
   - Include sanitization report in debug_info
   - Track if PII was potentially exposed

3. Create security event helpers:
   - `log_security_event(event_type: str, **details)` function
   - Predefined event types: AUTH_FAILURE, PERMISSION_DENIED, DATA_ACCESS
   - Automatic correlation with request context
   - Include in separate "security" log category

4. Add compliance metadata to logs:
   - Data retention hints (via log level or context)
   - Geographic origin (from request headers/IP)
   - Purpose/consent tracking (via context)
   - Regulatory flags (GDPR, CCPA, etc.)

**Implementation Notes**:
- SanitizationReport should be lightweight
- Security events should use structured format
- Compliance metadata should be optional
- Use existing RequestContext for correlation

**Testing Approach**:
- Test sanitization reporting accuracy
- Verify security event formatting
- Test compliance metadata propagation
- Test performance impact of reporting
- Verify no sensitive data in reports

**Acceptance Criteria**:
- Sanitization metrics available for debugging
- Security events properly structured
- Compliance metadata in logs when needed
- No performance degradation > 1ms
- Reports don't leak sensitive data

---

## Implementation Dependencies and Order

### Dependencies Between Tasks
1. **Task 3.1** (Pattern Detection) extends the existing sanitization - do first
2. **Task 3.2** (Strategies) depends on 3.1 for the enhanced patterns
3. **Task 3.3** (Performance) optimizes everything from 3.1 and 3.2
4. **Task 3.4** (Monitoring) adds observability to the entire system

### Key Integration Points
- All tasks build on `src/core/error_context.py` as the central module
- Configuration extends `LogConfig` from Task 1.1
- Performance optimizations affect all logging paths
- Must maintain compatibility with existing sanitization calls

### Testing Considerations
1. **Security Testing**:
   - Test with real PII patterns (in isolated environment)
   - Verify no data leakage in any scenario
   - Test with malicious inputs

2. **Performance Testing**:
   - Baseline current sanitization performance
   - Measure impact at each task
   - Load test with high-volume logging

3. **Integration Testing**:
   - Test with full request pipeline
   - Verify error handler integration
   - Test with various content types

### Risk Mitigation
- Each task maintains backward compatibility
- Performance optimizations are optional via config
- Caching can be disabled if issues arise
- All new features have feature flags

### Success Metrics
- Zero sensitive data leaked in logs
- Sanitization performance improved by 50%+
- Configuration allows fine-tuning
- Debugging easier with sanitization reports
- Compliance requirements trackable
