# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Database lifecycle management with startup checks and graceful shutdown
- Complete middleware integration with security headers, correlation IDs, and request logging
- Docker commands in Makefile for simplified container management and development workflow
- Docker Compose configuration for development and production environments
- Shellcheck integration for shell script linting in CI/CD and pre-commit hooks
- Docker infrastructure for production and development environments with multi-stage builds
- Health check endpoint (/health) for container orchestration and monitoring with database status reporting
- Cloud Run compatibility with PORT environment variable support
- Initial database migration baseline for schema version control
- Alembic database migration framework with full async SQLAlchemy support
- Automatic database migrations for test fixtures during test execution
- Comprehensive migration management commands in Makefile (create, up, down, history, etc.)
- Async database session management with connection pooling and automatic cleanup
- Database base model with auto-incrementing IDs, timestamps, and naming conventions
- Pyright type checking integration for VS Code compatibility
- PostgreSQL test database setup infrastructure with wait-for-postgres.sh script
- Test environment database URLs for pytest-env configuration
- Docker infrastructure for PostgreSQL database testing setup
- Docker Compose configuration for PostgreSQL 17 with health checks
- Database configuration with async PostgreSQL support and connection pooling
- Database dependencies for async PostgreSQL support (SQLAlchemy 2.0, asyncpg, Alembic, greenlet)
- Parallel-safe Docker integration tests with unique container names per test worker
- Parallel test execution support with isolated databases for each pytest-xdist worker
- FastAPI database dependency injection with automatic session lifecycle management
- Generic base repository pattern with type-safe CRUD operations
- Extended base repository with update, delete, count, and exists methods
- Dynamic filtering methods (filter_by and find_one_by) for flexible database queries
- Testing philosophy documentation outlining current and future testing strategies
- FastAPI best practices validation guide for ensuring code quality and consistency
- CLAUDE.md documentation for AI-assisted development guidance
- Task analysis and review commands for improved planning
- Enhanced logging configuration with advanced features for sampling, async logging, and request filtering
- Advanced context management for logging with size limits, nested contexts, and selective unbinding

### Changed
- Centralized all constants into a dedicated module for better maintainability and consistency
- Enhanced task breakdown command with stricter requirements
- Enhanced check-implementation command with clearer validation scope and improved section structure
- Enhanced check-implementation command with dependency version and Docker integration validation
- Uvicorn moved to production dependencies for container deployments
- Database default configuration updated to match Docker PostgreSQL credentials
- Environment variable structure fixed in .env.example for nested configuration
- Database implementation plan updated to use sequential IDs instead of UUIDs for better performance
- Test suite organization with consistent pytest markers on all test files
- Test structure refactored to use class-based organization for better maintainability
- README documentation updated with comprehensive database infrastructure details
- README comprehensively updated with middleware architecture, Docker workflows, API endpoints, and migration system documentation
- README documentation enhanced with parallel test execution, database fixtures, and Docker testing infrastructure details
- CLAUDE.md development guidance expanded with database architecture, observability patterns, and infrastructure setup
- CLAUDE.md documentation enhanced with Docker workflow, configuration patterns, and Cloud Run deployment guidance
- Test suite standardized to use pytest-mock fixtures instead of unittest.mock for better test isolation
- Project documentation reorganized into .specs directory for better structure
- Claude command templates introduced for standardized task management

### Removed
- do command from Claude command list as redundant with existing development workflow
- Obsolete plan.md file superseded by modular specification approach

### Fixed
- Database credentials standardized across documentation to match Docker setup (tributum/tributum_pass)
- CI pipeline failure due to missing docker/scripts directory
- pytest-rich and pytest-xdist compatibility issue for parallel test execution
- Structlog warning about format_exc_info in development logging
- Test fixture timeouts in CI environments by configuring pytest to apply timeouts only to test functions
- Intermittent Docker container startup failures in CI caused by network creation conflicts

## [0.3.0] - 2025-06-20

### Added
- /do command for expert-level task execution with quality enforcement guidelines
- /check-implementation command to verify code quality and adherence to project patterns
- McCabe complexity checking (C90) with maximum complexity of 10
- Claude Code slash command for automated GitHub release creation
- Enhanced /readme command with dual-mode operation: comprehensive discovery for initial generation and efficient incremental updates
- /curate-makefile command for intelligent Makefile analysis and improvement
- /analyze-project command for comprehensive project configuration and quality analysis
- JSON logging for staging environment to match production configuration
- pytest-randomly integration for randomized test execution to detect inter-test dependencies
- pytest-check integration for soft assertions that show all test failures at once
- OpenTelemetry observability configuration for distributed tracing control
- OpenTelemetry tracing infrastructure with GCP Cloud Trace integration for distributed tracing
- FastAPI instrumentation with OpenTelemetry for automatic request tracing

### Changed
- Enhanced /do command with stricter requirements for following project patterns and avoiding generic code
- Updated README with comprehensive observability features and distributed tracing documentation
- Streamlined CLAUDE.md from 480 to 317 lines while preserving all essential guidance for improved readability
- Enhanced CLAUDE.md with actionable development guidance including specific test commands, error patterns, and debugging tips
- Comprehensive CLAUDE.md rewrite with enhanced development guidance and architectural documentation
- Isolated development tool execution system to prevent dependency conflicts
- Unified command execution through Makefile for CI/CD, pre-commit, and local development
- Regenerated README with comprehensive project documentation following strict current-state-only principles
- Enhanced /readme command with stricter content validation to prevent future-looking documentation
- Enforced stricter type checking by removing ANN401 ignore rule and documenting all Any type usage
- Improved exception handling by removing BLE001 ignore rule and using specific exception types
- Added stricter linting rules (G, INP, T20) for improved code quality and security
- Refactored linting configuration to enable all Ruff rules by default with targeted exclusions
- Updated README with accurate 98% code coverage badge and latest tooling improvements
- Achieved 100% test coverage by adding comprehensive test suites for all edge cases
- Integrated pytest-env for centralized test environment configuration and reduced test boilerplate
- Updated README with comprehensive testing enhancements and configuration documentation

### Fixed
- Type safety issue in request logging test
- Import organization and type annotation linting issues
- RequestContext test isolation issue exposed by randomized test ordering

### Security
- Updated urllib3 to 2.5.0 to address security vulnerabilities

## [0.2.0] - 2025-06-17

### Added
- Initial project structure with FastAPI framework
- Configuration management using Pydantic Settings v2
- Exception infrastructure with severity levels and context support
- Structured logging with structlog and correlation ID support
- RequestContextMiddleware for request tracking
- High-performance JSON serialization with ORJSONResponse
- Comprehensive development tooling (ruff, mypy, pre-commit hooks)
- Security scanning with bandit, safety, pip-audit, and semgrep
- Test infrastructure with pytest and coverage reporting
- Domain-driven design structure (planned)
- Project metadata and semantic versioning setup
- Automated changelog updates in commit workflow
- Security headers middleware with configurable HSTS support
- Request logging middleware with comprehensive sanitization for observability
- Claude Code slash command for enforcing quality standards without bypasses
- Request/response body logging with automatic sensitive data sanitization
- Global exception handling with standardized error responses and full context logging
- HTTP request context capture for enhanced error reporting with security filtering
- Centralized constants module for magic values and configuration
- Request ID field for individual request tracking in error responses
- Debug information in error responses for development environments

### Changed
- Replaced interrogate with pydoclint for enhanced docstring quality validation
- Improved documentation quality across all modules with comprehensive docstrings
- Improved changelog commit messages to be more descriptive and follow project standards
- Enhanced Ruff linting configuration with stricter rules for code quality
- Refactored codebase to eliminate magic values and improve code quality

## [0.1.0] - 2025-06-16

### Added
- Initial release
- Basic FastAPI application with /info endpoint
- Core utilities for configuration, exceptions, and logging
- Development environment setup

[Unreleased]: https://github.com/daniel-jorge/tributum-back/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/daniel-jorge/tributum-back/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/daniel-jorge/tributum-back/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/daniel-jorge/tributum-back/releases/tag/v0.1.0
