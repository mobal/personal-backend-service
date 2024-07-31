terraform {
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }
  required_version = "~> 1"
}
