output "terraform_state_bucket" {
  description = "The name of the Terraform state bucket"
  value       = google_storage_bucket.terraform_state.name
}

output "terraform_locks_bucket" {
  description = "The name of the Terraform locks bucket"
  value       = google_storage_bucket.terraform_locks.name
}

output "backend_config" {
  description = "Backend configuration to use in other Terraform configurations"
  value = <<-EOT
    terraform {
      backend "gcs" {
        bucket = "${google_storage_bucket.terraform_state.name}"
        prefix = "terraform/state"
      }
    }
  EOT
}