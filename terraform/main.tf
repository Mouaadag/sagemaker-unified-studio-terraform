# SageMaker Unified Studio Infrastructure
# Purpose: MLOps platform for data science teams with testing capabilities

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  # Ready for HCP Terraform integration
  # cloud {
  #   organization = "your-org-name"
  #   workspaces {
  #     name = "sagemaker-unified-studio"
  #   }
  # }
}

provider "aws" {
  region = var.aws_region

  # Minimal default tags to avoid S3 conflicts
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  # Resource naming
  resource_suffix = random_id.suffix.hex
  bucket_name     = "${var.project_name}-studio-artifacts-${local.resource_suffix}"

  # Comprehensive tags for non-S3 resources
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner_email
    Service     = "sagemaker-unified-studio"
    CostCenter  = var.cost_center
    CreatedDate = formatdate("YYYY-MM-DD", timestamp())
    Purpose     = "MLOps-Platform"
  }
}
