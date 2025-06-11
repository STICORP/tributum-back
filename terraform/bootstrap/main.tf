terraform {
  required_version = ">= 1.10.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.15.0"
    }
  }
}

provider "google" {
  credentials = file(var.gcp_credentials_file)
  project     = var.project_id
  region      = var.region
}

# Enable required APIs
resource "google_project_service" "storage_api" {
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

# Create the bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name          = "${var.project_id}-terraform-state"
  location      = var.region
  force_destroy = false
  
  # Enable versioning for state file history
  versioning {
    enabled = true
  }
  
  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  depends_on = [google_project_service.storage_api]
}

# Create a bucket for other Terraform resources (locks, etc.)
resource "google_storage_bucket" "terraform_locks" {
  name          = "${var.project_id}-terraform-locks"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  depends_on = [google_project_service.storage_api]
}