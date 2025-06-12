variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "tributum-new"
}

variable "region" {
  description = "The GCP region for the state bucket"
  type        = string
  default     = "us-central1"
}

variable "gcp_credentials_file" {
  description = "Path to the GCP service account credentials JSON file"
  type        = string
  default     = "../../.keys/tributum-new-infrastructure-as-code-ce93f5144008.json"
}
