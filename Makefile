.PHONY: help install run dev lint lint-fix format format-check type-check pyright complexity-check security security-bandit security-deps security-safety security-pip-audit security-semgrep pre-commit pre-commit-ci test test-unit test-integration test-coverage test-fast test-verbose test-failed test-precommit test-ci migrate-create migrate-up migrate-down migrate-history migrate-current migrate-check migrate-init migrate-reset clean dead-code dead-code-report docstring-check docstring-missing docstring-quality pylint-check shellcheck shellcheck-fix all-checks

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

lint-fix:  ## Fix linting issues
	uv run ruff check --fix .

format:  ## Format code
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
	./scripts/tool safety scan --continue-on-error || true

security-pip-audit:  ## Run pip-audit vulnerability scan
	uv run pip-audit

security-semgrep:  ## Run semgrep static analysis
	./scripts/tool semgrep . --config=auto --error

pre-commit:  ## Run all pre-commit hooks
	uv run pre-commit run --all-files

pre-commit-ci:  ## Run pre-commit hooks for CI (with diff on failure)
	uv run pre-commit run --all-files --show-diff-on-failure

test:  ## Run all tests
	uv run pytest

test-unit:  ## Run unit tests only
	uv run pytest -m unit

test-integration:  ## Run integration tests only
	uv run pytest -m integration

test-coverage:  ## Run tests with coverage report
	uv run pytest --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-fast:  ## Run tests in parallel
	uv run pytest -n auto

test-verbose:  ## Run tests with verbose output
	uv run pytest -vv

test-failed:  ## Re-run only failed tests
	uv run pytest --lf

test-precommit:  ## Run tests for pre-commit (fast, no coverage)
	uv run pytest -x --tb=short --no-cov

test-ci:  ## Run tests for CI (stop on first failure)
	uv run pytest -x --tb=short

test-random:  ## Run tests with random ordering (shows seed in output)
	uv run pytest --randomly-dont-reorganize

test-seed:  ## Run tests with specific seed (usage: make test-seed SEED=12345)
	uv run pytest --randomly-seed=$(SEED)

test-no-random:  ## Run tests without randomization (for debugging)
	uv run pytest -p no:randomly

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
	find . -type f -name "interrogate_badge.svg" -delete
	find . -type f -name "dead-code-report.txt" -delete

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

all-checks: format-check lint type-check pyright complexity-check security dead-code docstring-check pylint-check shellcheck  ## Run all checks including dead code, docstring quality, and shell scripts
