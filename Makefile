.PHONY: help install lint format type-check security test clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	uv sync
	uv run pre-commit install

lint:  ## Run linting checks
	uv run ruff check .

lint-fix:  ## Fix linting issues
	uv run ruff check --fix .

format:  ## Format code
	uv run ruff format .

format-check:  ## Check code formatting
	uv run ruff format --check .

type-check:  ## Run type checking
	uv run mypy .

security:  ## Run all security checks
	uv run bandit -r . -c pyproject.toml
	uv run pip-audit
	@echo "Note: 'safety check' is deprecated. Use 'safety scan' instead."
	uv run safety scan || true

security-bandit:  ## Run Bandit security scan
	uv run bandit -r . -c pyproject.toml

security-deps:  ## Check dependencies for vulnerabilities
	uv run pip-audit
	uv run safety scan || true

pre-commit:  ## Run all pre-commit hooks
	uv run pre-commit run --all-files

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

all-checks: lint format-check type-check security  ## Run all checks (lint, format, type, security)
