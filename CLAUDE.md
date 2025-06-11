# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tributum is currently an empty project in its initial setup phase. The project name suggests it may be related to financial, tax, or payment systems.

## Project Status

- **Current State**: Python project initialized with uv, Terraform infrastructure setup complete
- **Technology Stack**: 
  - Backend: Python 3.13
  - Infrastructure: Terraform with GCP
- **Build System**: uv (Python package manager)

## Development Setup

### Infrastructure (Terraform)

- **GCP Project**: tributum-new
- **Service Account Key**: Located at `.keys/tributum-new-infrastructure-as-code-ce93f5144008.json`
- **Terraform State**: Stored remotely in GCS bucket `tributum-new-terraform-state`
- **Directory Structure**:
  - `terraform/` - Main infrastructure configuration
  - `terraform/bootstrap/` - Bootstrap configuration for state bucket (one-time setup)

### Terraform Commands

```bash
# Initialize Terraform (from terraform/ directory)
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply
```

**Note**: The service account key path is hardcoded in both the backend configuration and as a variable. This is necessary because Terraform backends cannot use variables.

## Development Guidelines

### Library Version Policy
- **ALWAYS use the absolutely latest version of any library** when adding dependencies
- Only use older versions if there are compatibility issues with other project dependencies
- This policy ensures we have the latest features, performance improvements, and security patches

### Git Commit Policy
- **NEVER include AI tool references in commit messages**
- Do not add "Generated with Claude Code" or similar attributions
- Do not include "Co-Authored-By: Claude" or any AI authorship
- Follow the conventional commit format without any AI mentions

## FastAPI Project Structure

Follow domain-driven design with domain-centric organization:

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py         # FastAPI app initialization
│   └── v1/
│       ├── __init__.py
│       ├── endpoints/  # API endpoints by domain
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── users.py
│       │   └── [other_endpoints].py
│       └── dependencies.py  # API-wide dependencies
├── domain/             # Business domains with all related code
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── schemas.py      # Pydantic models (DTOs)
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── repository.py   # Data access layer
│   │   ├── service.py      # Business logic
│   │   ├── exceptions.py   # Domain-specific exceptions
│   │   └── constants.py    # Domain constants
│   ├── users/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── exceptions.py
│   │   └── constants.py
│   └── [other_domains]/
│       └── (same structure)
├── infrastructure/     # Technical infrastructure only
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py      # Database connection/session management
│   │   ├── base.py         # Base model and repository classes
│   │   └── migrations/     # Alembic migrations
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis.py
│   └── external/           # Third-party integrations
│       ├── __init__.py
│       ├── email.py
│       └── storage.py
├── core/               # Application-wide shared code
│   ├── __init__.py
│   ├── config.py           # Settings management
│   ├── security.py         # Security utilities
│   ├── exceptions.py       # Base exceptions
│   └── utils.py           # Common utilities
└── cli/                # CLI commands
    ├── __init__.py
    └── commands.py

tests/                  # Mirror src structure
├── unit/
│   ├── domain/
│   │   ├── auth/
│   │   └── users/
│   └── core/
├── integration/
│   ├── api/
│   └── domain/
├── conftest.py        # Pytest fixtures
└── factories.py       # Test data factories

scripts/               # Development and deployment scripts
├── start.sh
├── test.sh
└── migrate.sh

config/                # Configuration files
├── .env.example
├── logging.yaml
└── gunicorn.conf.py
```

### Key Design Decisions:

1. **Domain-Centric Organization**: Each domain contains all its related code including models, repositories, schemas, and business logic
2. **Cohesive Domains**: Everything needed to understand and work with a domain is in one place
3. **Infrastructure for Technical Concerns**: Infrastructure layer only contains technical utilities (DB sessions, cache, external services)
4. **Shared Base Classes**: Common base classes for models and repositories live in infrastructure/database
5. **Clear Boundaries**: Each domain is self-contained but can depend on core utilities

This structure promotes domain cohesion while maintaining clean separation between business logic and technical infrastructure.

## Notes

This file should be updated as the project develops to include:
- Build, test, and lint commands once a technology stack is chosen
- High-level architecture decisions as they are made
- Key development workflows specific to this project
