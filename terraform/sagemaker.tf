# SageMaker Unified Studio resources for ML development and deployment

# SageMaker Unified Studio Domain
resource "aws_sagemaker_domain" "unified_studio_domain" {
  domain_name             = "${var.project_name}-unified-studio-${local.resource_suffix}"
  auth_mode               = "IAM"
  vpc_id                  = local.vpc_id
  subnet_ids              = local.subnet_ids
  app_network_access_type = var.app_network_access_type

  # Domain settings for unified studio
  domain_settings {
    security_group_ids             = local.security_group_ids
    execution_role_identity_config = "DISABLED"

    # RStudio settings (optional)
    dynamic "r_studio_server_pro_domain_settings" {
      for_each = var.rstudio_connect_url != "" ? [1] : []
      content {
        domain_execution_role_arn    = aws_iam_role.sagemaker_domain_execution_role.arn
        r_studio_connect_url         = var.rstudio_connect_url
        r_studio_package_manager_url = var.rstudio_package_manager_url
        default_resource_spec {
          instance_type               = "system"
          sagemaker_image_arn         = var.studio_default_image_arn != "" ? var.studio_default_image_arn : null
          sagemaker_image_version_arn = var.studio_default_image_version_arn != "" ? var.studio_default_image_version_arn : null
        }
      }
    }
  }

  # Default user settings
  default_user_settings {
    execution_role  = aws_iam_role.sagemaker_user_profile_role.arn
    security_groups = local.security_group_ids

    sharing_settings {
      notebook_output_option = "Allowed"
      s3_output_path         = "s3://${aws_s3_bucket.ml_artifacts.bucket}/studio-shared"
      s3_kms_key_id          = var.kms_key_id != "" ? var.kms_key_id : null
    }

    # Jupyter server app settings
    jupyter_server_app_settings {
      default_resource_spec {
        instance_type               = "system"
        sagemaker_image_arn         = var.studio_default_image_arn != "" ? var.studio_default_image_arn : null
        sagemaker_image_version_arn = var.studio_default_image_version_arn != "" ? var.studio_default_image_version_arn : null
      }
    }

    # Kernel gateway app settings  
    kernel_gateway_app_settings {
      default_resource_spec {
        instance_type               = "system"
        sagemaker_image_arn         = var.studio_default_image_arn != "" ? var.studio_default_image_arn : null
        sagemaker_image_version_arn = var.studio_default_image_version_arn != "" ? var.studio_default_image_version_arn : null
      }
    }

    # Canvas app settings (if enabled)
    dynamic "canvas_app_settings" {
      for_each = var.enable_canvas ? [1] : []
      content {
        time_series_forecasting_settings {
          status                   = "ENABLED"
          amazon_forecast_role_arn = aws_iam_role.sagemaker_canvas_forecast_role.arn
        }
        model_register_settings {
          status                                = "ENABLED"
          cross_account_model_register_role_arn = aws_iam_role.sagemaker_user_profile_role.arn
        }
        workspace_settings {
          s3_artifact_path = "s3://${aws_s3_bucket.ml_artifacts.bucket}/canvas-workspace"
          s3_kms_key_id    = var.kms_key_id != "" ? var.kms_key_id : null
        }
        generative_ai_settings {
          amazon_bedrock_role_arn = aws_iam_role.sagemaker_bedrock_role.arn
        }
      }
    }

    # R session app settings (if enabled)
    dynamic "r_session_app_settings" {
      for_each = var.studio_r_image_arn != "" ? [1] : []
      content {
        default_resource_spec {
          instance_type               = "system"
          sagemaker_image_arn         = var.studio_r_image_arn
          sagemaker_image_version_arn = var.studio_r_image_version_arn != "" ? var.studio_r_image_version_arn : null
        }
      }
    }
  }

  # Enable data governance features
  app_security_group_management = "Service"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-unified-studio-${local.resource_suffix}"
    Team = "DataScience"
    Type = "UnifiedStudio"
  })
}

# Default user profile for the domain
resource "aws_sagemaker_user_profile" "default_user" {
  domain_id         = aws_sagemaker_domain.unified_studio_domain.id
  user_profile_name = "${var.project_name}-default-user"

  user_settings {
    execution_role = aws_iam_role.sagemaker_user_profile_role.arn

    # Override default settings if needed
    sharing_settings {
      notebook_output_option = "Allowed"
      s3_output_path         = "s3://${aws_s3_bucket.ml_artifacts.bucket}/user-shared"
      s3_kms_key_id          = var.kms_key_id != "" ? var.kms_key_id : null
    }

    jupyter_server_app_settings {
      default_resource_spec {
        instance_type = "system"
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-default-user"
    Type = "DefaultUser"
  })
}

# Additional user profiles for domain users
resource "aws_sagemaker_user_profile" "domain_users" {
  for_each = { for user in var.domain_users : user.name => user }

  domain_id         = aws_sagemaker_domain.unified_studio_domain.id
  user_profile_name = each.value.name

  user_settings {
    execution_role = coalesce(each.value.execution_role_arn, aws_iam_role.sagemaker_user_profile_role.arn)

    sharing_settings {
      notebook_output_option = "Allowed"
      s3_output_path         = "s3://${aws_s3_bucket.ml_artifacts.bucket}/users/${each.value.name}"
      s3_kms_key_id          = var.kms_key_id != "" ? var.kms_key_id : null
    }

    jupyter_server_app_settings {
      default_resource_spec {
        instance_type = "system"
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = each.value.name
    Type = "DomainUser"
    User = each.value.name
  })
}
