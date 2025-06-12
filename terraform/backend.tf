# Backend configuration for Terraform state storage
terraform {
  backend "gcs" {
    bucket      = "tributum-new-terraform-state"
    prefix      = "terraform/state"
    credentials = "../.keys/tributum-new-infrastructure-as-code-ce93f5144008.json"
  }
}
