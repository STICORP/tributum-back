terraform {
  required_version = ">= 1.10.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.15.0"
    }
  }
  
  backend "gcs" {
    bucket      = "tributum-new-terraform-state"
    prefix      = "terraform/environments/staging"
    credentials = "../../../.keys/tributum-new-infrastructure-as-code-ce93f5144008.json"
  }
}

provider "google" {
  credentials = file(var.gcp_credentials_file)
  project     = var.project_id
  region      = var.region
}

# Staging environment specific resources
# Add your staging-specific resources here