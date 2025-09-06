# Networking resources for SageMaker Unified Studio

# Data source for default VPC if not provided
data "aws_vpc" "default" {
  count   = var.vpc_id == "" ? 1 : 0
  default = true
}

# Data source for default subnets if not provided
data "aws_subnets" "default" {
  count = length(var.subnet_ids) == 0 ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id]
  }
}

# Security group for SageMaker Domain
resource "aws_security_group" "sagemaker_studio_sg" {
  count       = length(var.security_group_ids) == 0 ? 1 : 0
  name        = "${var.project_name}-sagemaker-studio-sg-${local.resource_suffix}"
  description = "Security group for SageMaker Studio domain"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id

  # Allow outbound HTTPS for package downloads and AWS API calls
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound for AWS APIs and package downloads"
  }

  # Allow outbound HTTP for package repositories
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP outbound for package repositories"
  }

  # Allow NFS traffic for EFS (if needed)
  egress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    description = "NFS traffic for EFS storage"
  }

  # Self-referencing rule for internal communication
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
    description = "Internal communication within Studio"
  }

  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
    description = "Internal communication within Studio"
  }

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-sagemaker-studio-sg-${local.resource_suffix}"
    Purpose = "SageMakerStudio"
  })
}

# Local values for networking
locals {
  vpc_id             = var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id
  subnet_ids         = length(var.subnet_ids) > 0 ? var.subnet_ids : data.aws_subnets.default[0].ids
  security_group_ids = length(var.security_group_ids) > 0 ? var.security_group_ids : [aws_security_group.sagemaker_studio_sg[0].id]
}

# VPC Flow Logs for CIS Compliance
resource "aws_flow_log" "sagemaker_vpc" {
  count           = var.vpc_id == "" ? 0 : 1 # Only create if using custom VPC
  iam_role_arn    = aws_iam_role.flow_log[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_log[0].arn
  traffic_type    = "ALL"
  vpc_id          = local.vpc_id

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-vpc-flow-logs"
    Purpose = "SecurityCompliance"
  })
}

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_log" {
  count             = var.vpc_id == "" ? 0 : 1 # Only create if using custom VPC
  name              = "/aws/vpc/flowlogs/${var.project_name}"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Purpose = "VPCFlowLogs"
  })
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "flow_log" {
  count = var.vpc_id == "" ? 0 : 1 # Only create if using custom VPC
  name  = "${var.project_name}-vpc-flow-log-role-${local.resource_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "flow_log" {
  count = var.vpc_id == "" ? 0 : 1 # Only create if using custom VPC
  name  = "${var.project_name}-vpc-flow-log-policy"
  role  = aws_iam_role.flow_log[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}
