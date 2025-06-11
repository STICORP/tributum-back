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

Follow domain-driven design with consistent module organization:

```
src/
├── auth/
│   ├── router.py       # Endpoints
│   ├── schemas.py      # Pydantic models
│   ├── models.py       # Database models
│   ├── service.py      # Business logic
│   ├── dependencies.py # Route dependencies
│   ├── constants.py    # Module constants
│   ├── config.py       # Module config
│   └── exceptions.py   # Custom exceptions
├── [other_modules]/
│   └── (same structure as above)
└── core/
    ├── config.py       # Global configuration
    ├── database.py     # Database connection
    ├── dependencies.py # Common dependencies
    └── exceptions.py   # Base exceptions
```

Each module is self-contained with its own router, schemas, models, and business logic.

## Notes

This file should be updated as the project develops to include:
- Build, test, and lint commands once a technology stack is chosen
- High-level architecture decisions as they are made
- Key development workflows specific to this project
