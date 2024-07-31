terraform {
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.5.0"
    }
    random = {
      source = "hashicorp/random"
      version = "~> 3.6.2"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.59.0"
    }
  }
  required_version = "~> 1.7"
}
