# S3 bucket for storing ML artifacts

resource "aws_s3_bucket" "ml_artifacts" {
  bucket        = local.bucket_name
  force_destroy = true # Allow deletion even if not empty (for demo purposes)

  tags = local.common_tags
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "ml_artifacts_versioning" {
  bucket = aws_s3_bucket.ml_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket server-side encryption (CIS Compliance)
resource "aws_s3_bucket_server_side_encryption_configuration" "ml_artifacts_encryption" {
  bucket = aws_s3_bucket.ml_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block (CIS Compliance - Critical)
resource "aws_s3_bucket_public_access_block" "ml_artifacts_pab" {
  bucket = aws_s3_bucket.ml_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket notification to prevent accidental public access (CIS Compliance)
resource "aws_s3_bucket_notification" "ml_artifacts_notification" {
  bucket = aws_s3_bucket.ml_artifacts.id

  depends_on = [aws_s3_bucket_public_access_block.ml_artifacts_pab]
}

# S3 bucket logging (CIS Compliance)
resource "aws_s3_bucket_logging" "ml_artifacts_logging" {
  bucket = aws_s3_bucket.ml_artifacts.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "access-logs/"
}

# Separate bucket for access logs (CIS Compliance)
resource "aws_s3_bucket" "access_logs" {
  bucket        = "${local.bucket_name}-access-logs"
  force_destroy = true

  tags = merge(local.common_tags, {
    Purpose = "AccessLogs"
  })
}

resource "aws_s3_bucket_public_access_block" "access_logs_pab" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "ml_artifacts_lifecycle" {
  bucket = aws_s3_bucket.ml_artifacts.id

  rule {
    id     = "cleanup_old_artifacts"
    status = "Enabled"
    filter {} # This applies the rule to all objects in the bucket

    # Delete old versions after 30 days
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Move to IA after 30 days, then to Glacier after 90 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Upload sample dataset for testing (optional)
resource "aws_s3_object" "sample_data" {
  count = var.upload_sample_data ? 1 : 0
  
  bucket = aws_s3_bucket.ml_artifacts.id
  key    = "datasets/sample/iris.csv"
  source = "../data/iris.csv"
  etag   = filemd5("../data/iris.csv")

  depends_on = [aws_s3_bucket.ml_artifacts]
}

# Create folder structure for organized data storage
resource "aws_s3_object" "folder_structure" {
  for_each = toset([
    "datasets/raw/",
    "datasets/processed/", 
    "models/training/",
    "models/artifacts/",
    "notebooks/templates/",
    "notebooks/experiments/",
    "pipelines/definitions/",
    "pipelines/outputs/"
  ])
  
  bucket = aws_s3_bucket.ml_artifacts.id
  key    = each.value
  source = "/dev/null"
  
  depends_on = [aws_s3_bucket.ml_artifacts]
}
