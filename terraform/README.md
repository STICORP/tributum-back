# Terraform Infrastructure

This directory contains Terraform configurations for managing GCP infrastructure.

## Prerequisites

1. Install Terraform (>= 1.10.0)
2. Have a GCP project and service account with appropriate permissions
3. Place your service account key at `.keys/infrastructure-as-code.json`

## Getting Started

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your GCP project details

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Plan your infrastructure:
   ```bash
   terraform plan
   ```

5. Apply the configuration:
   ```bash
   terraform apply
   ```

## Directory Structure

- `main.tf` - Main Terraform configuration
- `variables.tf` - Variable definitions
- `outputs.tf` - Output definitions
- `backend.tf` - Backend configuration (for remote state storage)
- `modules/` - Reusable Terraform modules
- `environments/` - Environment-specific configurations

## Security

- Never commit service account keys or `terraform.tfvars` to version control
- Always use least-privilege principles for service accounts
- Consider using remote state storage (GCS backend) for team collaboration
