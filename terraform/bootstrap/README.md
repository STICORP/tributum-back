# Terraform Bootstrap

This directory contains the bootstrap configuration to create the GCS bucket for storing Terraform state.

## Purpose

This is a one-time setup that creates:
- A GCS bucket for storing Terraform state files
- A GCS bucket for storing Terraform locks

## Usage

1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Create the state bucket:
   ```bash
   terraform apply
   ```

3. Note the output values - you'll need the bucket name for the main Terraform configuration.

## Important Notes

- This configuration uses local state (stored in this directory)
- The state bucket has versioning enabled and deletion protection
- After creating the bucket, update the main Terraform configuration to use remote state
