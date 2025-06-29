# Phase 0: Cleanup and Preparation

## Overview
This phase prepares the codebase for the new simplified observability implementation by removing all current observability and logging functionality. Since the software is not live and in early development, we can do a direct removal without migration concerns.

## Objectives
1. Remove all current observability and logging modules
2. Remove structlog dependency
3. Clean up all imports throughout the codebase
4. Remove tests related to the old implementation
5. Update middleware to minimal functionality
6. Prepare configuration for new implementation
7. **Update constants.py files to remove obsolete constants**
8. **Comprehensively update .env.example**
9. **Update Docker and CI configurations**

## Files to Remove Completely

### Core Modules (2,319 lines to remove)
- `src/core/logging.py` (875 lines)
- `src/core/error_context.py` (589 lines)
- `src/core/observability.py` (733 lines)
- `src/api/middleware/request_logging.py` (855 lines) - Will be recreated in Phase 2

### Test Files to Remove (323 test functions)
- `tests/unit/core/test_logging.py`
- `tests/unit/core/test_error_context.py`
- `tests/unit/core/test_observability.py`
- `tests/unit/api/middleware/test_request_logging.py`
- Any other test files that specifically test logging/observability features

## Files to Update

### 1. Update All Imports
Replace throughout the codebase:
```python
# OLD
from src.core.logging import get_logger
logger = get_logger(__name__)

# TEMPORARY (Phase 0)
# TODO: Will be replaced with loguru in Phase 1
import logging
logger = logging.getLogger(__name__)
```

### 2. Update Middleware

#### `src/api/middleware/error_handler.py`
- Remove imports from `src.core.logging`
- Use standard logging temporarily
- Keep error response structure intact

#### `src/api/middleware/request_context.py`
- Keep as-is (this middleware stays)
- Remove any logging-specific imports
- Correlation ID functionality remains

#### `src/api/main.py`
- Remove `RequestLoggingMiddleware` registration
- Remove observability setup calls
- Keep other middleware intact

### 3. Update Configuration

#### `src/core/config.py`
Simplify LogConfig to minimal:
```python
class LogConfig(BaseModel):
    """Minimal logging configuration for Phase 0."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

class ObservabilityConfig(BaseModel):
    """Minimal observability configuration for Phase 0."""

    enable_tracing: bool = Field(
        default=False,
        description="Tracing disabled in Phase 0",
    )
```

Remove all other logging/observability configuration fields.

### 4. Update Dependencies

#### `pyproject.toml`
Remove:
```toml
# Remove from dependencies
"structlog>=25.4.0",
```

Keep:
```toml
# Keep these for later phases
"opentelemetry-api>=1.34.1",
"opentelemetry-sdk>=1.34.1",
"opentelemetry-instrumentation-fastapi>=0.55b1",
"opentelemetry-instrumentation-sqlalchemy>=0.55b1",
```

### 5. Update Constants Files

#### `src/core/constants.py`
Remove logging-specific constants:
```python
# REMOVE these constants:
FINGERPRINT_MAX_PARTS = 5
MAX_CONTEXT_SIZE = 10000
MAX_CONTEXT_DEPTH = 10
MAX_VALUE_SIZE = 1000
TRUNCATED_SUFFIX = "... [TRUNCATED]"
MIN_CONTAINER_ID_LENGTH = 12
EXCEPTION_TUPLE_MIN_LENGTH = 3
TRACEBACK_FRAMES_TO_INCLUDE = 3

# KEEP these constants (will be used in Phase 4):
REDACTED = "[REDACTED]"
# Note: SENSITIVE_FIELD_PATTERNS will be replaced with a simpler regex in Phase 4
```

#### `src/api/constants.py`
Keep all constants - they're still relevant:
- `CORRELATION_ID_HEADER` - Used in middleware
- `SENSITIVE_HEADERS` - Will be used in Phase 4

### 6. Update .env.example

Create a backup first:
```bash
cp .env.example .env.example.backup
```

Remove ALL of these obsolete settings:
```bash
# REMOVE these logging settings (40+ lines):
LOG_CONFIG__RENDER_JSON_LOGS
LOG_CONFIG__ADD_TIMESTAMP
LOG_CONFIG__TIMESTAMPER_FORMAT
LOG_CONFIG__SAMPLING_RATE
LOG_CONFIG__ENABLE_ASYNC_LOGGING
LOG_CONFIG__ASYNC_QUEUE_SIZE
LOG_CONFIG__LOG_REQUEST_BODY
LOG_CONFIG__LOG_RESPONSE_BODY
LOG_CONFIG__MAX_BODY_LOG_SIZE
LOG_CONFIG__ENABLE_PERFORMANCE_METRICS
LOG_CONFIG__TRACK_REQUEST_DURATION
LOG_CONFIG__TRACK_ACTIVE_TASKS
LOG_CONFIG__TRACK_REQUEST_SIZES
LOG_CONFIG__ENABLE_MEMORY_TRACKING
LOG_CONFIG__CRITICAL_REQUEST_THRESHOLD_MS
LOG_CONFIG__ENABLE_PERFORMANCE_PROCESSOR
LOG_CONFIG__ENABLE_ENVIRONMENT_PROCESSOR
LOG_CONFIG__ENABLE_ERROR_CONTEXT_PROCESSOR
LOG_CONFIG__SENSITIVE_VALUE_DETECTION
LOG_CONFIG__ADDITIONAL_SENSITIVE_PATTERNS
LOG_CONFIG__EXCLUDED_FIELDS_FROM_SANITIZATION
LOG_CONFIG__DEFAULT_SANITIZATION_STRATEGY
LOG_CONFIG__FIELD_SANITIZATION_STRATEGIES

# REMOVE these observability settings:
OBSERVABILITY_CONFIG__SERVICE_NAME
OBSERVABILITY_CONFIG__ENABLE_METRICS
OBSERVABILITY_CONFIG__METRICS_EXPORT_INTERVAL_MS
OBSERVABILITY_CONFIG__ENABLE_SYSTEM_METRICS
OBSERVABILITY_CONFIG__SYSTEM_METRICS_INTERVAL_S
```

Keep only these simplified settings (temporarily):
```bash
# Logging Configuration (Simplified for Phase 0)
LOG_CONFIG__LOG_LEVEL=INFO
LOG_CONFIG__LOG_FORMAT=console  # Will become LOG_FORMATTER_TYPE in Phase 1
LOG_CONFIG__EXCLUDED_PATHS=["/health", "/metrics"]
LOG_CONFIG__SLOW_REQUEST_THRESHOLD_MS=1000
LOG_CONFIG__ENABLE_SQL_LOGGING=false
LOG_CONFIG__SLOW_QUERY_THRESHOLD_MS=100
LOG_CONFIG__SENSITIVE_FIELDS=["password", "token", "secret", "api_key", "authorization"]

# Observability Configuration (Simplified for Phase 0)
OBSERVABILITY_CONFIG__ENABLE_TRACING=false
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=1.0
```

Update the example configurations section to remove references to deleted settings.

### 7. Create Configuration Migration Script

Create `scripts/phase0_config_migration.py`:
```python
#!/usr/bin/env python3
"""Phase 0: Configuration and constants migration."""

import re
from pathlib import Path

# Constants to remove from src/core/constants.py
CONSTANTS_TO_REMOVE = [
    "FINGERPRINT_MAX_PARTS",
    "MAX_CONTEXT_SIZE",
    "MAX_CONTEXT_DEPTH",
    "MAX_VALUE_SIZE",
    "TRUNCATED_SUFFIX",
    "MIN_CONTAINER_ID_LENGTH",
    "EXCEPTION_TUPLE_MIN_LENGTH",
    "TRACEBACK_FRAMES_TO_INCLUDE",
]

# Environment variables to remove from .env files
ENV_VARS_TO_REMOVE = [
    "LOG_CONFIG__RENDER_JSON_LOGS",
    "LOG_CONFIG__ADD_TIMESTAMP",
    "LOG_CONFIG__TIMESTAMPER_FORMAT",
    "LOG_CONFIG__SAMPLING_RATE",
    "LOG_CONFIG__ENABLE_ASYNC_LOGGING",
    "LOG_CONFIG__ASYNC_QUEUE_SIZE",
    # ... (add all 40+ variables)
]

def clean_constants_file(file_path: Path) -> None:
    """Remove obsolete constants from constants.py."""
    content = file_path.read_text()

    for constant in CONSTANTS_TO_REMOVE:
        # Remove constant definition line
        content = re.sub(f"^{constant} = .*$\n", "", content, flags=re.MULTILINE)

    # Clean up extra blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    file_path.write_text(content)
    print(f"Cleaned constants from {file_path}")

def clean_env_file(file_path: Path) -> None:
    """Remove obsolete environment variables."""
    if not file_path.exists():
        return

    lines = file_path.read_text().splitlines()
    cleaned_lines = []

    for line in lines:
        # Skip lines with obsolete variables
        if any(var in line for var in ENV_VARS_TO_REMOVE):
            continue
        # Keep the line
        cleaned_lines.append(line)

    file_path.write_text("\n".join(cleaned_lines) + "\n")
    print(f"Cleaned environment variables from {file_path}")

def main():
    """Run configuration migration."""
    print("Phase 0: Configuration Migration")
    print("=" * 50)

    # Clean constants files
    constants_files = [
        Path("src/core/constants.py"),
    ]

    for file_path in constants_files:
        if file_path.exists():
            clean_constants_file(file_path)

    # Clean environment files
    env_files = [
        Path(".env.example"),
        Path(".env"),
        Path(".env.development"),
        Path(".env.staging"),
        Path(".env.production"),
    ]

    for file_path in env_files:
        clean_env_file(file_path)

    print("\nConfiguration migration complete!")
    print("Next: Review and commit the changes")

if __name__ == "__main__":
    main()
```

### 8. Update Docker and CI Configurations

#### docker-compose.yml
Remove obsolete environment variables from service definitions:
```yaml
# Remove from api service environment:
- LOG_CONFIG__ENABLE_PERFORMANCE_METRICS
- LOG_CONFIG__TRACK_ACTIVE_TASKS
- OBSERVABILITY_CONFIG__ENABLE_METRICS
# etc.
```

#### GitHub Actions Workflows
Update any workflow files that set environment variables:
```yaml
# Remove obsolete env vars from .github/workflows/*.yml
```

## Implementation Steps

### Step 1: Create Migration Script
Create `scripts/phase0_cleanup.py`:
```python
#!/usr/bin/env python3
"""Phase 0: Remove current observability implementation."""

import re
from pathlib import Path

def update_imports(file_path: Path) -> bool:
    """Update imports to use standard logging temporarily."""
    content = file_path.read_text()
    original = content

    # Replace get_logger imports
    content = re.sub(
        r'from src\.core\.logging import get_logger\s*\n\s*logger = get_logger\(__name__\)',
        'import logging\nlogger = logging.getLogger(__name__)',
        content,
        flags=re.MULTILINE
    )

    # Mark other logging imports for removal
    content = re.sub(
        r'from src\.core\.logging import .*',
        '# TODO: Remove this import - Phase 0 cleanup',
        content
    )

    # Mark error_context imports
    content = re.sub(
        r'from src\.core\.error_context import .*',
        '# TODO: Remove this import - Phase 0 cleanup',
        content
    )

    # Mark observability imports
    content = re.sub(
        r'from src\.core\.observability import .*',
        '# TODO: Remove this import - Phase 0 cleanup',
        content
    )

    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Run Phase 0 cleanup."""
    print("Phase 0: Cleanup and Preparation")
    print("=" * 50)

    # Update imports
    updated = 0
    for file_path in Path("src").rglob("*.py"):
        if update_imports(file_path):
            print(f"Updated: {file_path}")
            updated += 1

    print(f"\nTotal files updated: {updated}")
    print("\nNext steps:")
    print("1. Delete src/core/logging.py")
    print("2. Delete src/core/error_context.py")
    print("3. Delete src/core/observability.py")
    print("4. Delete src/api/middleware/request_logging.py")
    print("5. Remove related test files")
    print("6. Update pyproject.toml to remove structlog")
    print("7. Run 'make clean' to remove cached files")

if __name__ == "__main__":
    main()
```

### Step 2: Execute Cleanup
```bash
# Run the cleanup script
python scripts/phase0_cleanup.py

# Run configuration migration
python scripts/phase0_config_migration.py

# Remove the modules
rm src/core/logging.py
rm src/core/error_context.py
rm src/core/observability.py
rm src/api/middleware/request_logging.py

# Remove test files
rm tests/unit/core/test_logging.py
rm tests/unit/core/test_error_context.py
rm tests/unit/core/test_observability.py
rm tests/unit/api/middleware/test_request_logging.py

# Clean cached files
make clean
```

### Step 3: Update Remaining Files
Manually update:
1. `src/api/main.py` - Remove middleware registration
2. `src/core/config.py` - Simplify configuration classes
3. Any files with TODO comments from the script

### Step 4: Fix Broken Tests
Many tests will fail after removing logging. For each failing test:
1. If it tests logging behavior - remove it
2. If it uses logging for test assertions - update to not rely on logs
3. If it's a business logic test that happens to use logging - update imports

## Validation Checklist

- [ ] All logging/observability modules deleted
- [ ] All imports updated to use standard logging
- [ ] No references to `get_logger` remain
- [ ] No references to `structlog` remain
- [ ] `RequestLoggingMiddleware` removed from app
- [ ] Configuration simplified
- [ ] pyproject.toml updated
- [ ] **Constants cleaned in src/core/constants.py**
- [ ] **SENSITIVE_FIELD_PATTERNS marked for Phase 4 update**
- [ ] **.env.example updated (40+ settings removed)**
- [ ] **All .env files cleaned**
- [ ] **Docker-compose.yml environment variables updated**
- [ ] **CI/CD workflows updated**
- [ ] Tests pass (after cleanup)
- [ ] `make lint` passes
- [ ] `make type-check` passes

## Expected Test Results

After Phase 0:
- ~367 tests should still pass (non-logging tests)
- ~323 tests removed (logging-specific tests)
- Some tests may need minor updates to not rely on logging

## Notes for Next Phases

- Phase 1 will add Loguru and update all imports again
- Standard logging is only temporary for Phase 0
- Keep correlation ID functionality intact in RequestContextMiddleware
- Error response structure must remain unchanged

## Rollback

If needed, Phase 0 can be rolled back with:
```bash
git checkout pre-phase0-tag
```

But since this is early-stage software, rollback is unlikely to be needed.
