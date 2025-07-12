.PHONY: help install run dev \
	lint lint-fix format format-check type-check pyright complexity-check \
	security security-bandit security-deps security-safety security-pip-audit security-semgrep \
	pre-commit pre-commit-ci \
	test test-unit test-integration \
	test-coverage test-coverage-unit test-coverage-integration \
	test-fast test-fast-unit test-fast-integration \
	test-verbose test-verbose-unit test-verbose-integration \
	test-failed test-failed-unit test-failed-integration \
	test-precommit test-precommit-unit test-precommit-integration \
	test-ci test-ci-unit test-ci-integration \
	test-random test-random-unit test-random-integration \
	test-seed test-seed-unit test-seed-integration \
	test-no-random test-no-random-unit test-no-random-integration \
	migrate-create migrate-up migrate-down migrate-history migrate-current migrate-check migrate-init migrate-reset \
	clean dead-code dead-code-report docstring-check docstring-missing docstring-quality \
	pylint-check shellcheck shellcheck-fix all-checks all-fixes \
	mock-check markers-check \
	docker-build docker-up docker-up-dev docker-down docker-clean docker-logs docker-shell docker-psql docker-test docker-migrate docker-build-production docker-build-dev

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	uv sync --all-extras --dev
	uv run pre-commit install

run:  ## Run the FastAPI application
	uv run python main.py

dev:  ## Run FastAPI in development mode with auto-reload
	uv run uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

lint:  ## Run linting checks
	uv run ruff check .

lint-fix:  ## Fix linting issues (includes imports, whitespace, line length)
	uv run ruff check --fix .

format:  ## Format code (includes whitespace cleanup, newlines)
	uv run ruff format .

format-check:  ## Check code formatting
	uv run ruff format --check .

type-check:  ## Run type checking with MyPy
	uv run mypy .

pyright:  ## Run Pyright/Pylance type checking
	uv run pyright

complexity-check:  ## Check code complexity (McCabe)
	uv run ruff check . --select C90

security:  ## Run all security checks
	$(MAKE) security-bandit
	$(MAKE) security-pip-audit
	$(MAKE) security-safety
	$(MAKE) security-semgrep

security-bandit:  ## Run Bandit security scan
	uv run bandit -r . -c pyproject.toml

security-deps:  ## Check dependencies for vulnerabilities
	$(MAKE) security-pip-audit
	$(MAKE) security-safety

security-safety:  ## Run safety vulnerability scan
	@true | ./scripts/tool safety scan --continue-on-error || true

security-pip-audit:  ## Run pip-audit vulnerability scan
	uv run pip-audit

security-semgrep:  ## Run semgrep static analysis
	./scripts/tool semgrep . --config=auto --error

pre-commit:  ## Run all pre-commit hooks
	uv run pre-commit run --all-files

pre-commit-ci:  ## Run pre-commit hooks for CI (with diff on failure)
	uv run pre-commit run --all-files --show-diff-on-failure

test:  ## Run all tests (unit then integration)
	@echo "Running unit tests..."
	@$(MAKE) test-unit
	@echo "\nRunning integration tests..."
	@$(MAKE) test-integration

test-unit:  ## Run unit tests only
	uv run pytest -m unit --ignore=tests/integration

test-integration:  ## Run integration tests only
	uv run pytest -m integration --ignore=tests/unit

test-coverage:  ## Run all tests with coverage report
	@echo "Running unit tests with coverage..."
	@$(MAKE) test-coverage-unit
	@echo "\nRunning integration tests with coverage..."
	@$(MAKE) test-coverage-integration
	@echo "Combined coverage report generated in htmlcov/index.html"

test-coverage-unit:  ## Run unit tests with coverage report
	uv run pytest -m unit --ignore=tests/integration --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-coverage-integration:  ## Run integration tests with coverage report
	uv run pytest -m integration --ignore=tests/unit --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-fast:  ## Run all tests in parallel
	@echo "Running unit tests in parallel..."
	@$(MAKE) test-fast-unit
	@echo "\nRunning integration tests in parallel..."
	@$(MAKE) test-fast-integration

test-fast-unit:  ## Run unit tests in parallel
	uv run pytest -m unit --ignore=tests/integration -n auto

test-fast-integration:  ## Run integration tests in parallel
	uv run pytest -m integration --ignore=tests/unit -n auto

test-verbose:  ## Run all tests with verbose output
	@echo "Running unit tests with verbose output..."
	@$(MAKE) test-verbose-unit
	@echo "\nRunning integration tests with verbose output..."
	@$(MAKE) test-verbose-integration

test-verbose-unit:  ## Run unit tests with verbose output
	uv run pytest -m unit --ignore=tests/integration -vv

test-verbose-integration:  ## Run integration tests with verbose output
	uv run pytest -m integration --ignore=tests/unit -vv

test-failed:  ## Re-run only failed tests
	@echo "Re-running failed unit tests..."
	@$(MAKE) test-failed-unit
	@echo "\nRe-running failed integration tests..."
	@$(MAKE) test-failed-integration

test-failed-unit:  ## Re-run only failed unit tests
	uv run pytest -m unit --ignore=tests/integration --lf

test-failed-integration:  ## Re-run only failed integration tests
	uv run pytest -m integration --ignore=tests/unit --lf

test-precommit:  ## Run tests for pre-commit (fast, no coverage)
	@echo "Running unit tests for pre-commit..."
	@$(MAKE) test-precommit-unit
	@echo "\nRunning integration tests for pre-commit..."
	@$(MAKE) test-precommit-integration

test-precommit-unit:  ## Run unit tests for pre-commit (fast, no coverage)
	uv run pytest -m unit --ignore=tests/integration -x --tb=short --no-cov

test-precommit-integration:  ## Run integration tests for pre-commit (fast, no coverage)
	uv run pytest -m integration --ignore=tests/unit -x --tb=short --no-cov

test-ci:  ## Run all tests for CI (stop on first failure)
	@echo "Running unit tests for CI..."
	@$(MAKE) test-ci-unit
	@echo "\nRunning integration tests for CI..."
	@$(MAKE) test-ci-integration

test-ci-unit:  ## Run unit tests for CI
	uv run pytest -m unit --ignore=tests/integration -x --tb=short

test-ci-integration:  ## Run integration tests for CI
	uv run pytest -m integration --ignore=tests/unit -x --tb=short

test-random:  ## Run all tests with random ordering (shows seed in output)
	@echo "Running unit tests with random ordering..."
	@$(MAKE) test-random-unit
	@echo "\nRunning integration tests with random ordering..."
	@$(MAKE) test-random-integration

test-random-unit:  ## Run unit tests with random ordering
	uv run pytest -m unit --ignore=tests/integration --randomly-dont-reorganize

test-random-integration:  ## Run integration tests with random ordering
	uv run pytest -m integration --ignore=tests/unit --randomly-dont-reorganize

test-seed:  ## Run all tests with specific seed (usage: make test-seed SEED=12345)
	@echo "Running unit tests with seed $(SEED)..."
	@$(MAKE) test-seed-unit SEED=$(SEED)
	@echo "\nRunning integration tests with seed $(SEED)..."
	@$(MAKE) test-seed-integration SEED=$(SEED)

test-seed-unit:  ## Run unit tests with specific seed (usage: make test-seed-unit SEED=12345)
	uv run pytest -m unit --ignore=tests/integration --randomly-seed=$(SEED)

test-seed-integration:  ## Run integration tests with specific seed (usage: make test-seed-integration SEED=12345)
	uv run pytest -m integration --ignore=tests/unit --randomly-seed=$(SEED)

test-no-random:  ## Run all tests without randomization (for debugging)
	@echo "Running unit tests without randomization..."
	@$(MAKE) test-no-random-unit
	@echo "\nRunning integration tests without randomization..."
	@$(MAKE) test-no-random-integration

test-no-random-unit:  ## Run unit tests without randomization
	uv run pytest -m unit --ignore=tests/integration -p no:randomly

test-no-random-integration:  ## Run integration tests without randomization
	uv run pytest -m integration --ignore=tests/unit -p no:randomly

mock-check:  ## Check for forbidden unittest.mock imports in test files
	uv run python scripts/check-mock-imports.py

markers-check:  ## Check that test files have appropriate pytest markers
	uv run python scripts/check-test-markers.py

# Database migration commands
migrate-create:  ## Create new migration (usage: make migrate-create MSG="add users table")
	@if [ -z "$(MSG)" ]; then echo "Error: MSG is required. Usage: make migrate-create MSG=\"your message\""; exit 1; fi
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-up:  ## Run all pending migrations
	uv run alembic upgrade head

migrate-down:  ## Downgrade one migration
	uv run alembic downgrade -1

migrate-history:  ## Show migration history
	uv run alembic history --verbose

migrate-current:  ## Show current migration revision
	uv run alembic current

migrate-check:  ## Check if there are pending model changes
	uv run alembic check

migrate-init:  ## Initialize database with all migrations (useful for fresh installs)
	@echo "Initializing database with all migrations..."
	uv run alembic upgrade head
	@echo "Database initialization complete!"

migrate-reset:  ## Reset database (drop all tables and re-run migrations) - DESTRUCTIVE!
	@echo "WARNING: This will drop all tables and data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	uv run alembic downgrade base
	uv run alembic upgrade head
	@echo "Database reset complete!"

clean:  ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type f -name ".coverage.*" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type f -name "interrogate_badge.svg" -delete
	find . -type f -name "dead-code-report.txt" -delete
	find . -type d -name ".hypothesis" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name ".benchmarks" -exec rm -rf {} +
	find . -type d -name "prof" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name "pip-wheel-metadata" -exec rm -rf {} +
	find . -type f -name "*.orig" -delete
	find . -type f -name "*~" -delete
	find . -type f -name "*.bak" -delete

dead-code:  ## Check for dead code using vulture
	uv run vulture . --config=pyproject.toml

dead-code-report:  ## Generate detailed dead code report
	uv run vulture . --config=pyproject.toml --sort-by-size > dead-code-report.txt
	@echo "Dead code report saved to dead-code-report.txt"

docstring-check:  ## Check docstring presence and quality
	@echo "Checking for missing docstrings..."
	uv run ruff check . --select D100,D101,D102,D103,D104 || true
	@echo "\nChecking docstring quality..."
	uv run pydoclint src/ --config=pyproject.toml

docstring-missing:  ## Show only missing docstrings
	uv run ruff check . --select D100,D101,D102,D103,D104

docstring-quality:  ## Check only docstring quality (not presence)
	uv run pydoclint src/ --config=pyproject.toml

pylint-check:  ## Run pylint for code quality checks
	uv run pylint --rcfile=pyproject.toml src/

shellcheck:  ## Run shellcheck on all shell scripts
	@echo "Running shellcheck on shell scripts..."
	@find . -type f \( -name "*.sh" -o -name "*.bash" \) -not -path "./.venv/*" -not -path "./venv/*" -not -path "./.git/*" -exec uv run shellcheck {} +
	@if [ -f scripts/tool ]; then uv run shellcheck scripts/tool; fi

shellcheck-fix:  ## Run shellcheck with auto-fix suggestions
	@echo "Running shellcheck with fix suggestions..."
	@find . -type f \( -name "*.sh" -o -name "*.bash" \) -not -path "./.venv/*" -not -path "./venv/*" -not -path "./.git/*" -exec uv run shellcheck -f diff {} \; | patch -p1

all-checks: format lint type-check pyright complexity-check security dead-code docstring-check pylint-check shellcheck mock-check markers-check  ## Run all quality checks before committing

all-fixes: format lint-fix ## Run all safe auto-fixes

# Docker commands
docker-build:  ## Build all Docker images
	docker-compose build

docker-up:  ## Start all services (production mode)
	docker-compose up -d

docker-up-dev:  ## Start development environment with hot-reload
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-down:  ## Stop all services
	docker-compose down

docker-clean:  ## Clean all Docker resources
	docker-compose down -v --remove-orphans

docker-logs:  ## View logs (use SERVICE=api for specific service)
	docker-compose logs -f $${SERVICE:-}

docker-shell:  ## Shell into API container
	docker-compose exec api /bin/bash

docker-psql:  ## Connect to PostgreSQL
	docker-compose exec postgres psql -U tributum -d tributum_db

docker-test:  ## Run tests in Docker
	docker-compose -f docker-compose.test.yml run --rm api uv run pytest

docker-migrate:  ## Run database migrations in a separate container
	docker-compose run --rm api bash /app/docker/scripts/migrate.sh

docker-build-production:  ## Build production image only
	docker build -f docker/app/Dockerfile -t tributum:production .

docker-build-dev:  ## Build development image only
	docker build -f docker/app/Dockerfile.dev -t tributum:development .
