#!/usr/bin/env python3
"""
Enterprise MLOps Notification Manager
Handles notifications for training, deployment, and pipeline events
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import boto3
except ImportError:
    print("Warning: boto3 not available for SNS notifications")

from .config import PipelineConfig


class NotificationManager:
    """Manages notifications for MLOps pipeline events"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = self._setup_logging()
        
        # Initialize notification clients
        self.sns_client = None
        if self.config.SNS_TOPIC_ARN:
            try:
                self.sns_client = boto3.client('sns', region_name=self.config.AWS_REGION)
            except Exception as e:
                self.logger.warning(f"Failed to initialize SNS client: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(self.config.LOG_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _format_accuracy(self, accuracy: float) -> str:
        """Format accuracy as percentage"""
        return f"{accuracy * 100:.2f}%"
    
    def _send_sns_notification(self, subject: str, message: str) -> bool:
        """Send SNS notification"""
        if not self.sns_client or not self.config.SNS_TOPIC_ARN:
            return False
            
        try:
            self.sns_client.publish(
                TopicArn=self.config.SNS_TOPIC_ARN,
                Subject=subject,
                Message=message
            )
            self.logger.info(f"✅ SNS notification sent: {subject}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to send SNS notification: {e}")
            return False
    
    def _send_slack_notification(self, message: Dict[str, Any]) -> bool:
        """Send Slack notification via webhook"""
        if not self.config.SLACK_WEBHOOK_URL:
            return False
            
        try:
            data = json.dumps(message).encode('utf-8')
            req = urllib.request.Request(
                self.config.SLACK_WEBHOOK_URL,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                if response.getcode() == 200:
                    self.logger.info("✅ Slack notification sent")
                    return True
                else:
                    self.logger.error(f"❌ Slack notification failed: {response.getcode()}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to send Slack notification: {e}")
            return False
    
    def send_success_notification(self, pipeline_results: Dict[str, Any]) -> None:
        """Send notification for successful training with deployment recommendation"""
        evaluation = pipeline_results.get('evaluation_results', {})
        accuracy = evaluation.get('accuracy', 0.0)
        should_deploy = pipeline_results.get('should_deploy', False)
        
        # SNS notification
        subject = f"🎉 MLOps Training Success - {self._format_accuracy(accuracy)} Accuracy"
        
        sns_message = f"""
MLOps Training Pipeline Completed Successfully

📊 Model Performance:
• Accuracy: {self._format_accuracy(accuracy)}
• CV Accuracy: {self._format_accuracy(evaluation.get('cv_mean_accuracy', 0.0))}
• Threshold: {self._format_accuracy(self.config.ACCURACY_THRESHOLD)}

🚀 Deployment Decision:
• Deploy Recommended: {"✅ YES" if should_deploy else "❌ NO"}
• Reason: {pipeline_results.get('deployment_reason', 'Unknown')}

⏱️ Pipeline Duration: {pipeline_results.get('pipeline_duration', 0):.2f} seconds
🏷️ Training Job: {pipeline_results.get('sagemaker_training_job', 'Local only')}
📅 Timestamp: {pipeline_results.get('pipeline_timestamp')}

Next Steps:
{f"• Model is ready for deployment" if should_deploy else "• Review model performance and retrain if needed"}
• Check SageMaker console for details
• Review evaluation metrics in S3
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        color = "good" if should_deploy else "warning"
        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"🎉 MLOps Training Complete - {self._format_accuracy(accuracy)} Accuracy",
                    "fields": [
                        {
                            "title": "Model Accuracy",
                            "value": self._format_accuracy(accuracy),
                            "short": True
                        },
                        {
                            "title": "Deploy Ready",
                            "value": "✅ YES" if should_deploy else "❌ NO",
                            "short": True
                        },
                        {
                            "title": "Training Job",
                            "value": pipeline_results.get('sagemaker_training_job', 'Local only'),
                            "short": False
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.info(f"📢 Training success notifications sent")
    
    def send_failure_notification(self, pipeline_results: Dict[str, Any]) -> None:
        """Send notification for training that doesn't meet deployment criteria"""
        evaluation = pipeline_results.get('evaluation_results', {})
        accuracy = evaluation.get('accuracy', 0.0)
        
        # SNS notification
        subject = f"⚠️ MLOps Training - Low Accuracy {self._format_accuracy(accuracy)}"
        
        sns_message = f"""
MLOps Training Pipeline - Model Below Deployment Threshold

📊 Model Performance:
• Accuracy: {self._format_accuracy(accuracy)}
• Required Threshold: {self._format_accuracy(self.config.ACCURACY_THRESHOLD)}
• Minimum Threshold: {self._format_accuracy(self.config.MINIMUM_ACCURACY)}

❌ Deployment Decision: NOT RECOMMENDED
• Reason: {pipeline_results.get('deployment_reason', 'Below accuracy threshold')}

⏱️ Pipeline Duration: {pipeline_results.get('pipeline_duration', 0):.2f} seconds
📅 Timestamp: {pipeline_results.get('pipeline_timestamp')}

Recommended Actions:
• Review model hyperparameters
• Check data quality and preprocessing
• Consider feature engineering improvements
• Increase training data if available
• Review model architecture
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        slack_message = {
            "attachments": [
                {
                    "color": "danger",
                    "title": f"⚠️ MLOps Training - Low Accuracy {self._format_accuracy(accuracy)}",
                    "fields": [
                        {
                            "title": "Model Accuracy",
                            "value": self._format_accuracy(accuracy),
                            "short": True
                        },
                        {
                            "title": "Required",
                            "value": self._format_accuracy(self.config.ACCURACY_THRESHOLD),
                            "short": True
                        },
                        {
                            "title": "Action Required",
                            "value": "Model retraining recommended",
                            "short": False
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.info(f"📢 Training failure notifications sent")
    
    def send_deployment_success_notification(self, deployment_results: Dict[str, Any]) -> None:
        """Send notification for successful deployment"""
        endpoint_name = deployment_results.get('endpoint_name')
        duration = deployment_results.get('deployment_duration', 0)
        
        # SNS notification
        subject = f"🚀 MLOps Deployment Success - {endpoint_name}"
        
        sns_message = f"""
Model Deployment Completed Successfully

🎯 Endpoint Details:
• Endpoint Name: {endpoint_name}
• Status: InService
• Deployment Duration: {duration:.2f} seconds

🧪 Health Check:
• Status: {deployment_results.get('test_results', {}).get('status', 'Unknown')}
• Latency: {deployment_results.get('test_results', {}).get('test_duration_ms', 0):.2f}ms

📅 Deployment Time: {deployment_results.get('metadata', {}).get('deployment_timestamp')}

The model is now ready for production use!
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        slack_message = {
            "attachments": [
                {
                    "color": "good",
                    "title": f"🚀 Deployment Success",
                    "fields": [
                        {
                            "title": "Endpoint",
                            "value": endpoint_name,
                            "short": False
                        },
                        {
                            "title": "Duration",
                            "value": f"{duration:.2f}s",
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": "✅ InService",
                            "short": True
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.info(f"📢 Deployment success notifications sent")
    
    def send_deployment_failure_notification(self, deployment_results: Dict[str, Any]) -> None:
        """Send notification for failed deployment"""
        error = deployment_results.get('error', 'Unknown error')
        duration = deployment_results.get('deployment_duration', 0)
        
        # SNS notification
        subject = f"❌ MLOps Deployment Failed"
        
        sns_message = f"""
Model Deployment Failed

❌ Error Details:
• Error: {error}
• Duration: {duration:.2f} seconds
• Attempted Endpoint: {deployment_results.get('attempted_endpoint', 'Unknown')}

🔄 Rollback Status:
{f"• Rollback: {deployment_results.get('rollback_results', {}).get('status', 'Not attempted')}" if deployment_results.get('rollback_results') else "• Rollback: Not configured"}

Action Required:
• Check SageMaker logs for detailed error information
• Verify IAM permissions and resource limits
• Review model artifacts and inference code
• Consider instance type or configuration changes
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        slack_message = {
            "attachments": [
                {
                    "color": "danger",
                    "title": "❌ Deployment Failed",
                    "fields": [
                        {
                            "title": "Error",
                            "value": error,
                            "short": False
                        },
                        {
                            "title": "Duration",
                            "value": f"{duration:.2f}s",
                            "short": True
                        },
                        {
                            "title": "Action",
                            "value": "Manual intervention required",
                            "short": True
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.info(f"📢 Deployment failure notifications sent")
    
    def send_deployment_skipped_notification(self, skip_info: Dict[str, Any]) -> None:
        """Send notification when deployment is skipped"""
        training_job = skip_info.get('training_job_name')
        reason = skip_info.get('reason')
        evaluation = skip_info.get('evaluation_results', {})
        accuracy = evaluation.get('accuracy', 0.0)
        
        # SNS notification
        subject = f"⏸️ MLOps Deployment Skipped - {training_job}"
        
        sns_message = f"""
Model Deployment Skipped

📊 Model Details:
• Training Job: {training_job}
• Accuracy: {self._format_accuracy(accuracy)}
• Required: {self._format_accuracy(self.config.ACCURACY_THRESHOLD)}

⏸️ Skip Reason: {reason}

To deploy this model:
• Enable auto-deploy in configuration
• Manually trigger deployment if accuracy is acceptable
• Retrain model to meet accuracy threshold
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        slack_message = {
            "attachments": [
                {
                    "color": "warning",
                    "title": "⏸️ Deployment Skipped",
                    "fields": [
                        {
                            "title": "Training Job",
                            "value": training_job,
                            "short": False
                        },
                        {
                            "title": "Accuracy",
                            "value": self._format_accuracy(accuracy),
                            "short": True
                        },
                        {
                            "title": "Reason",
                            "value": reason,
                            "short": True
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.info(f"📢 Deployment skipped notifications sent")
    
    def send_error_notification(self, error_results: Dict[str, Any]) -> None:
        """Send notification for pipeline errors"""
        error = error_results.get('error', 'Unknown error')
        duration = error_results.get('pipeline_duration', 0)
        
        # SNS notification
        subject = f"🚨 MLOps Pipeline Error"
        
        sns_message = f"""
MLOps Pipeline Encountered an Error

🚨 Error Details:
• Error: {error}
• Duration: {duration:.2f} seconds
• Timestamp: {error_results.get('pipeline_timestamp')}

Action Required:
• Check pipeline logs for detailed error information
• Verify AWS permissions and service limits
• Review configuration and input parameters
• Contact MLOps team if error persists
"""
        
        self._send_sns_notification(subject, sns_message)
        
        # Slack notification
        slack_message = {
            "attachments": [
                {
                    "color": "danger",
                    "title": "🚨 Pipeline Error",
                    "fields": [
                        {
                            "title": "Error",
                            "value": error,
                            "short": False
                        },
                        {
                            "title": "Duration",
                            "value": f"{duration:.2f}s",
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": "❌ Failed",
                            "short": True
                        }
                    ],
                    "footer": "MLOps Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        self._send_slack_notification(slack_message)
        
        self.logger.error(f"📢 Pipeline error notifications sent")
