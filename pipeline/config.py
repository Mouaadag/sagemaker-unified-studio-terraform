#!/usr/bin/env python3
"""
Enterprise MLOps Pipeline Configuration
Defines accuracy thresholds, notification settings, and deployment parameters
"""

import os
from typing import Any, Dict


class PipelineConfig:
    """Configuration for the MLOps pipeline"""
    
    # Model accuracy thresholds
    ACCURACY_THRESHOLD = float(os.getenv('ACCURACY_THRESHOLD', '0.95'))  # 95% default
    MINIMUM_ACCURACY = float(os.getenv('MINIMUM_ACCURACY', '0.90'))      # 90% minimum
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    INSTANCE_TYPE = os.getenv('INSTANCE_TYPE', 'ml.m5.large')
    
    # S3 Paths
    S3_BUCKET = os.getenv('S3_BUCKET', 'sagemaker-mlops-artifacts')
    MODEL_ARTIFACTS_PREFIX = 'models'
    EVALUATION_RESULTS_PREFIX = 'evaluations'
    
    # Notification Configuration
    SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', None)
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', None)
    EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS', '').split(',') if os.getenv('EMAIL_RECIPIENTS') else []
    
    # Pipeline Settings
    MAX_TRAINING_TIME = int(os.getenv('MAX_TRAINING_TIME', '3600'))  # 1 hour in seconds
    AUTO_DEPLOY_ENABLED = os.getenv('AUTO_DEPLOY_ENABLED', 'true').lower() == 'true'
    ROLLBACK_ON_FAILURE = os.getenv('ROLLBACK_ON_FAILURE', 'true').lower() == 'true'
    
    # Model Settings
    MODEL_NAME_PREFIX = os.getenv('MODEL_NAME_PREFIX', 'iris-classifier')
    ENDPOINT_PREFIX = os.getenv('ENDPOINT_PREFIX', 'iris-model')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'accuracy_threshold': cls.ACCURACY_THRESHOLD,
            'minimum_accuracy': cls.MINIMUM_ACCURACY,
            'aws_region': cls.AWS_REGION,
            'instance_type': cls.INSTANCE_TYPE,
            's3_bucket': cls.S3_BUCKET,
            'auto_deploy_enabled': cls.AUTO_DEPLOY_ENABLED,
            'rollback_on_failure': cls.ROLLBACK_ON_FAILURE,
            'model_name_prefix': cls.MODEL_NAME_PREFIX,
            'endpoint_prefix': cls.ENDPOINT_PREFIX
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings"""
        if cls.ACCURACY_THRESHOLD < 0 or cls.ACCURACY_THRESHOLD > 1:
            raise ValueError("ACCURACY_THRESHOLD must be between 0 and 1")
        
        if cls.MINIMUM_ACCURACY < 0 or cls.MINIMUM_ACCURACY > 1:
            raise ValueError("MINIMUM_ACCURACY must be between 0 and 1")
        
        if cls.ACCURACY_THRESHOLD < cls.MINIMUM_ACCURACY:
            raise ValueError("ACCURACY_THRESHOLD must be >= MINIMUM_ACCURACY")
        
        return True
