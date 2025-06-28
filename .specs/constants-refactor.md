# Constants Refactoring Plan

This document outlines the step-by-step plan to refactor constants into configurable settings and remove unused constants from the codebase.

## Overview

The refactoring will:
1. Remove unused constants
2. Convert deployment-specific constants to settings
3. Standardize HTTP status codes using FastAPI's status module
4. Maintain 100% test coverage throughout

## Task List

### Phase 1: Preparation and Config Structure

#### Task 1.1: Create new config sections [🔲 Pending]
- **File**: `src/core/config.py`
- **Action**: Add new configuration models
  - Create `APIConfig` model with `default_pagination_limit: int = 100`
  - Create `SecurityConfig` model with `hsts_max_age: int = 31536000`
  - Extend `LogConfig` with:
    - `max_context_size: int = 10000`
    - `max_context_depth: int = 10`
    - `max_value_size: int = 1000`
    - `traceback_frames_to_include: int = 3`
  - Extend `DatabaseConfig` with:
    - `pool_recycle_seconds: int = 3600`
    - `command_timeout_seconds: int = 60`
- **Tests**: Update `test_config.py` to verify new fields with defaults

#### Task 1.2: Add new config sections to Settings class [🔲 Pending]
- **File**: `src/core/config.py`
- **Action**: Add to Settings class:
  - `api_config: APIConfig = Field(default_factory=APIConfig)`
  - `security_config: SecurityConfig = Field(default_factory=SecurityConfig)`
- **Tests**: Update settings tests to verify new sections

### Phase 2: Database Constants Migration

#### Task 2.1: Migrate POOL_RECYCLE_SECONDS to settings [🔲 Pending]
- **Files**:
  - `src/infrastructure/constants.py` - Remove `POOL_RECYCLE_SECONDS`
  - `src/infrastructure/database/session.py` - Update line using `pool_recycle=POOL_RECYCLE_SECONDS` to use `settings.database_config.pool_recycle_seconds`
- **Tests**: Update database session tests to use new setting

#### Task 2.2: Migrate COMMAND_TIMEOUT_SECONDS to settings [🔲 Pending]
- **Files**:
  - `src/infrastructure/constants.py` - Remove `COMMAND_TIMEOUT_SECONDS`
  - `src/infrastructure/database/session.py` - Update line using `command_timeout=COMMAND_TIMEOUT_SECONDS` to use `settings.database_config.command_timeout_seconds`
- **Tests**: Update database session tests

### Phase 3: API Constants Migration

#### Task 3.1: Migrate DEFAULT_PAGINATION_LIMIT to settings [🔲 Pending]
- **Files**:
  - `src/api/constants.py` - Remove `DEFAULT_PAGINATION_LIMIT`
  - `src/infrastructure/database/repository.py` - Update `limit: int = DEFAULT_PAGINATION_LIMIT` to use settings
- **Action**: Inject settings dependency or get from cached settings
- **Tests**: Update repository tests to verify pagination with new setting

#### Task 3.2: Migrate DEFAULT_HSTS_MAX_AGE to settings [🔲 Pending]
- **Files**:
  - `src/api/constants.py` - Remove `DEFAULT_HSTS_MAX_AGE`
  - `src/api/middleware/security_headers.py` - Update HSTS header to use `settings.security_config.hsts_max_age`
- **Tests**: Update security headers middleware tests

### Phase 4: Logging Constants Migration

#### Task 4.1: Migrate MAX_CONTEXT_SIZE, MAX_CONTEXT_DEPTH, MAX_VALUE_SIZE [🔲 Pending]
- **Files**:
  - `src/core/constants.py` - Remove these three constants
  - `src/core/logging.py` - Update `_sanitize_value` function to use settings
- **Action**: Get settings from cached `get_settings()`
- **Tests**: Update logging tests to verify context sanitization with new settings

#### Task 4.2: Migrate TRACEBACK_FRAMES_TO_INCLUDE [🔲 Pending]
- **Files**:
  - `src/core/constants.py` - Remove `TRACEBACK_FRAMES_TO_INCLUDE`
  - `src/core/logging.py` - Update traceback processing to use settings
- **Tests**: Update error logging tests

### Phase 5: Remove Unused Constants

#### Task 5.1: Remove unused API constants [🔲 Pending]
- **File**: `src/api/constants.py`
- **Action**: Remove:
  - `HTTP_200_OK`
  - `DEFAULT_API_PORT`
  - `MAX_BODY_SIZE`
- **Tests**: No test updates needed (unused constants)

#### Task 5.2: Remove unused core constants [🔲 Pending]
- **File**: `src/core/constants.py`
- **Action**: Remove:
  - `DEFAULT_LOG_MAX_LENGTH`
  - `MAX_ERROR_CONTEXT_LENGTH`
  - `STACK_FRAME_CONTEXT_LINES`
- **Tests**: No test updates needed (unused constants)

### Phase 6: HTTP Status Code Standardization

#### Task 6.1: Replace custom HTTP constants with FastAPI status [🔲 Pending]
- **File**: `src/api/middleware/error_handler.py`
- **Action**:
  - Remove import of HTTP constants from `api.constants`
  - Import `status` from `fastapi`
  - Replace all HTTP_* constants with `status.HTTP_*` equivalents
- **Tests**: Update error handler tests to use FastAPI status codes

#### Task 6.2: Remove HTTP status constants [🔲 Pending]
- **File**: `src/api/constants.py`
- **Action**: Remove all HTTP_* constants
- **Tests**: Verify no remaining imports of these constants

### Phase 7: Documentation and Cleanup

#### Task 7.1: Update .env.example [🔲 Pending]
- **File**: `.env.example`
- **Action**: Add new configuration examples:
  ```
  # API Configuration
  API_CONFIG__DEFAULT_PAGINATION_LIMIT=100

  # Security Configuration
  SECURITY_CONFIG__HSTS_MAX_AGE=31536000

  # Extended Logging Configuration
  LOG_CONFIG__MAX_CONTEXT_SIZE=10000
  LOG_CONFIG__MAX_CONTEXT_DEPTH=10
  LOG_CONFIG__MAX_VALUE_SIZE=1000
  LOG_CONFIG__TRACEBACK_FRAMES_TO_INCLUDE=3

  # Extended Database Configuration
  DATABASE_CONFIG__POOL_RECYCLE_SECONDS=3600
  DATABASE_CONFIG__COMMAND_TIMEOUT_SECONDS=60
  ```

#### Task 7.2: Run all checks and tests [🔲 Pending]
- **Action**:
  - Run `make all-checks` to ensure code quality
  - Run `make test` to ensure 100% coverage
  - Fix any issues that arise

## Implementation Notes

1. **Order of Implementation**: Tasks are ordered to minimize disruption. Database and API constants are migrated first as they have fewer dependencies.

2. **Testing Strategy**: After each task, run the specific tests for the affected modules before proceeding.

3. **Rollback Plan**: Each task is atomic. If issues arise, revert the specific task's changes.

4. **Settings Access Pattern**:
   - For middleware: Get settings in `__init__` or use dependency injection
   - For utilities: Use `get_settings()` cached function
   - For repositories: Consider dependency injection pattern

5. **Import Management**: When removing constants, ensure all imports are updated to prevent import errors.

## Success Criteria

- [ ] All unused constants removed
- [ ] All configurable values moved to settings
- [ ] HTTP status codes standardized on FastAPI's status module
- [ ] 100% test coverage maintained
- [ ] All quality checks pass (`make all-checks`)
- [ ] No breaking changes to external API
