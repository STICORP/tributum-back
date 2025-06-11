variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "gcp_credentials_file" {
  description = "Path to the GCP service account credentials JSON file"
  type        = string
  default     = "../.keys/tributum-new-infrastructure-as-code-ce93f5144008.json"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}
