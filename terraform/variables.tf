# Terraform variables for SageMaker ML deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "sagemaker-ml-demo"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Enhanced tagging variables
variable "owner_email" {
  description = "Email of the resource owner for accountability"
  type        = string
  default     = "admin@example.com"

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

variable "cost_center" {
  description = "Cost center for resource billing"
  type        = string
  default     = "ml-engineering"
}

variable "upload_sample_data" {
  description = "Whether to upload sample dataset for testing"
  type        = bool
  default     = true
}

variable "model_name" {
  description = "Name of the ML model"
  type        = string
  default     = "iris-classifier"
}

variable "training_instance_type" {
  description = "Instance type for SageMaker training"
  type        = string
  default     = "ml.m5.large"
}

variable "inference_instance_type" {
  description = "Instance type for SageMaker inference endpoint"
  type        = string
  default     = "ml.t2.medium"
}

variable "enable_auto_scaling" {
  description = "Enable auto scaling for the endpoint"
  type        = bool
  default     = false
}

variable "min_capacity" {
  description = "Minimum number of instances for auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of instances for auto scaling"
  type        = number
  default     = 3
}

variable "target_invocations_per_instance" {
  description = "Target invocations per instance for auto scaling"
  type        = number
  default     = 100
}

# SageMaker Notebook Instance Variables (Legacy - keeping for compatibility)
variable "notebook_instance_type" {
  description = "Instance type for SageMaker notebook"
  type        = string
  default     = "ml.t3.medium"
}

variable "notebook_volume_size" {
  description = "Volume size in GB for notebook instance"
  type        = number
  default     = 20
}

variable "enable_lifecycle_config" {
  description = "Enable lifecycle configuration for notebook instance"
  type        = bool
  default     = true
}

variable "default_code_repository" {
  description = "Default code repository URL for notebook instance"
  type        = string
  default     = ""
}

# SageMaker Unified Studio Variables
variable "vpc_id" {
  description = "VPC ID for SageMaker Domain (if not provided, will use default VPC)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for SageMaker Domain (if not provided, will use default subnets)"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for SageMaker Domain (if not provided, will create default)"
  type        = list(string)
  default     = []
}

variable "app_network_access_type" {
  description = "Network access type for SageMaker Studio apps"
  type        = string
  default     = "PublicInternetOnly"
  validation {
    condition     = contains(["PublicInternetOnly", "VpcOnly"], var.app_network_access_type)
    error_message = "App network access type must be either 'PublicInternetOnly' or 'VpcOnly'."
  }
}

variable "studio_default_instance_type" {
  description = "Default instance type for SageMaker Studio apps"
  type        = string
  default     = "ml.t3.medium"

  validation {
    condition     = can(regex("^ml\\.", var.studio_default_instance_type))
    error_message = "Instance type must start with 'ml.' prefix."
  }
}

variable "studio_user_instance_type" {
  description = "Instance type for user-specific Studio apps"
  type        = string
  default     = "ml.t3.medium"

  validation {
    condition     = can(regex("^ml\\.", var.studio_user_instance_type))
    error_message = "Instance type must start with 'ml.' prefix."
  }
}

variable "studio_default_image_arn" {
  description = "Default SageMaker image ARN for Studio (optional)"
  type        = string
  default     = ""
}

variable "studio_default_image_version_arn" {
  description = "Default SageMaker image version ARN for Studio (optional)"
  type        = string
  default     = ""
}

variable "studio_r_image_arn" {
  description = "R image ARN for Studio R sessions (optional)"
  type        = string
  default     = ""
}

variable "studio_r_image_version_arn" {
  description = "R image version ARN for Studio R sessions (optional)"
  type        = string
  default     = ""
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional)"
  type        = string
  default     = ""
}

variable "rstudio_connect_url" {
  description = "RStudio Connect URL (optional)"
  type        = string
  default     = ""
}

variable "rstudio_package_manager_url" {
  description = "RStudio Package Manager URL (optional)"
  type        = string
  default     = ""
}

variable "enable_canvas" {
  description = "Enable SageMaker Canvas for no-code ML"
  type        = bool
  default     = true
}

variable "enable_data_governance" {
  description = "Enable data governance features"
  type        = bool
  default     = true
}

variable "domain_users" {
  description = "List of users to create in the SageMaker domain"
  type = list(object({
    name               = string
    execution_role_arn = optional(string)
  }))
  default = [
    {
      name = "data-scientist-1"
    },
    {
      name = "ml-engineer-1"
    }
  ]
}

variable "create_vpc" {
  description = "Whether to create a VPC for SageMaker resources"
  type        = bool
  default     = false
}
