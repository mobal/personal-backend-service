terraform {
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "2.7.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  required_version = ">= 1.11"
}

provider "aws" {
  region = var.aws_region
}
