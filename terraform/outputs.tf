# Terraform outputs for SageMaker ML deployment

# S3 bucket outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for ML artifacts"
  value       = aws_s3_bucket.ml_artifacts.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for ML artifacts"
  value       = aws_s3_bucket.ml_artifacts.arn
}

# SageMaker Unified Studio Outputs
output "sagemaker_domain_info" {
  description = "Complete SageMaker Unified Studio domain information"
  value = {
    domain_id               = aws_sagemaker_domain.unified_studio_domain.id
    domain_arn              = aws_sagemaker_domain.unified_studio_domain.arn
    domain_url              = aws_sagemaker_domain.unified_studio_domain.url
    domain_name             = aws_sagemaker_domain.unified_studio_domain.domain_name
    home_efs_file_system_id = aws_sagemaker_domain.unified_studio_domain.home_efs_file_system_id
    security_group_id       = length(aws_security_group.sagemaker_studio_sg) > 0 ? aws_security_group.sagemaker_studio_sg[0].id : null
    vpc_id                  = local.vpc_id
    subnet_ids              = local.subnet_ids
  }
  sensitive = false
}

output "user_profiles_info" {
  description = "Information about all SageMaker user profiles"
  value = {
    default_user = {
      arn  = aws_sagemaker_user_profile.default_user.arn
      name = aws_sagemaker_user_profile.default_user.user_profile_name
    }
    domain_users = {
      for k, v in aws_sagemaker_user_profile.domain_users : k => {
        arn  = v.arn
        name = v.user_profile_name
      }
    }
  }
}

# IAM Role Outputs
output "sagemaker_domain_execution_role_arn" {
  description = "ARN of the SageMaker domain execution role"
  value       = aws_iam_role.sagemaker_domain_execution_role.arn
}

output "sagemaker_user_profile_role_arn" {
  description = "ARN of the SageMaker user profile role"
  value       = aws_iam_role.sagemaker_user_profile_role.arn
}

output "sagemaker_user_profile_role_name" {
  description = "Name of the SageMaker user profile role"
  value       = aws_iam_role.sagemaker_user_profile_role.name
}

output "sagemaker_domain_execution_role_name" {
  description = "Name of the SageMaker domain execution role"
  value       = aws_iam_role.sagemaker_domain_execution_role.name
}

output "sagemaker_domain_id" {
  description = "The ID of the SageMaker domain"
  value       = aws_sagemaker_domain.unified_studio_domain.id
}

output "sagemaker_default_user_profile_name" {
  description = "The name of the default user profile"
  value       = aws_sagemaker_user_profile.default_user.user_profile_name
}

output "aws_region" {
  description = "The AWS region where resources are deployed"
  value       = var.aws_region
}

output "sagemaker_canvas_forecast_role_arn" {
  description = "ARN of the SageMaker Canvas forecast role"
  value       = aws_iam_role.sagemaker_canvas_forecast_role.arn
}

output "sagemaker_bedrock_role_arn" {
  description = "ARN of the SageMaker Bedrock role"
  value       = aws_iam_role.sagemaker_bedrock_role.arn
}

# Networking Outputs
output "vpc_id" {
  description = "VPC ID used for SageMaker Domain"
  value       = local.vpc_id
}

output "subnet_ids" {
  description = "Subnet IDs used for SageMaker Domain"
  value       = local.subnet_ids
}

output "security_group_ids" {
  description = "Security group IDs used for SageMaker Domain"
  value       = local.security_group_ids
}

# Summary output for easy reference
output "deployment_summary" {
  description = "Comprehensive summary of deployed resources"
  value = {
    # Core Infrastructure
    project_name   = var.project_name
    environment    = var.environment
    aws_region     = data.aws_region.current.name
    aws_account_id = data.aws_caller_identity.current.account_id

    # Storage
    s3_bucket          = aws_s3_bucket.ml_artifacts.bucket
    s3_bucket_arn      = aws_s3_bucket.ml_artifacts.arn
    access_logs_bucket = aws_s3_bucket.access_logs.bucket

    # SageMaker Unified Studio
    studio_domain_id    = aws_sagemaker_domain.unified_studio_domain.id
    studio_domain_url   = aws_sagemaker_domain.unified_studio_domain.url
    studio_default_user = aws_sagemaker_user_profile.default_user.user_profile_name

    # Networking & Security
    vpc_id          = local.vpc_id
    security_groups = local.security_group_ids

    # IAM & Governance
    domain_execution_role = aws_iam_role.sagemaker_domain_execution_role.name
    user_profile_role     = aws_iam_role.sagemaker_user_profile_role.name

    # Compliance Features
    encryption_enabled     = "AES256"
    public_access_blocked  = true
    access_logging_enabled = true

    # Tags Applied
    common_tags = local.common_tags
  }
}

# Quick Start Instructions Output
output "quick_start_guide" {
  description = "Step-by-step instructions to get started with your SageMaker Unified Studio"
  value = {
    studio_access_url = aws_sagemaker_domain.unified_studio_domain.url
    steps = [
      "1. 🎯 Access SageMaker Unified Studio at: ${aws_sagemaker_domain.unified_studio_domain.url}",
      "2. 👤 Login with your AWS credentials and select user profile: ${aws_sagemaker_user_profile.default_user.user_profile_name}",
      "3. 🚀 Launch JupyterLab, RStudio, or Canvas apps from the Studio interface",
      "4. 📂 Your project files are automatically synced from S3: ${aws_s3_bucket.ml_artifacts.bucket}",
      "5. 📊 Use the data catalog to discover and govern your data assets",
      "6. 🤝 Collaborate with team members using shared notebooks and models",
      "7. 🎨 Try SageMaker Canvas for no-code ML model building",
      "8. 🤖 Access generative AI capabilities through integrated Bedrock",
      "9. 🔒 All activities are logged and governed with fine-grained access controls"
    ]
    compliance_features = [
      "✅ S3 public access blocked and encrypted",
      "✅ CloudWatch logging for all activities",
      "✅ IAM roles with least privilege access",
      "✅ Resource tagging for governance and billing"
    ]
  }
}
