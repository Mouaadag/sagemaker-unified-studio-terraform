#!/usr/bin/env python3
"""
Enterprise MLOps Deployment Pipeline
Handles conditional deployment based on model accuracy with rollback capabilities
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import boto3

try:
    import sagemaker
    from sagemaker import get_execution_role
    from sagemaker.sklearn.model import SKLearnModel
except ImportError:
    print("Warning: SageMaker SDK not available. Install with: pip install sagemaker")

from .config import PipelineConfig
from .notifications import NotificationManager


class DeploymentPipeline:
    """Enterprise-grade deployment pipeline with conditional deployment"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = self._setup_logging()
        self.notification_manager = NotificationManager()
        self.sagemaker_client = boto3.client('sagemaker', region_name=self.config.AWS_REGION)
        
        # Deployment tracking
        self.current_endpoint = None
        self.previous_endpoint = None
        self.deployment_metadata = {}
        
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
    
    def get_latest_training_job(self) -> Optional[str]:
        """Find the most recent completed training job"""
        self.logger.info("🔍 Searching for latest completed training job")
        
        try:
            response = self.sagemaker_client.list_training_jobs(
                SortBy='CreationTime',
                SortOrder='Descending',
                MaxResults=20
            )
            
            # Look for iris-related jobs first
            for job in response['TrainingJobs']:
                if (job['TrainingJobStatus'] == 'Completed' and 
                    self.config.MODEL_NAME_PREFIX in job['TrainingJobName']):
                    self.logger.info(f"✅ Found training job: {job['TrainingJobName']}")
                    return job['TrainingJobName']
            
            # Fallback to any completed job
            for job in response['TrainingJobs']:
                if job['TrainingJobStatus'] == 'Completed':
                    self.logger.warning(f"⚠️ Using fallback training job: {job['TrainingJobName']}")
                    return job['TrainingJobName']
            
            self.logger.error("❌ No completed training jobs found")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error finding training job: {str(e)}")
            return None
    
    def check_deployment_criteria(self, training_job_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if model meets deployment criteria based on evaluation metrics
        
        Args:
            training_job_name: Name of the training job
            
        Returns:
            Tuple of (should_deploy: bool, evaluation_metrics: dict)
        """
        self.logger.info(f"📊 Checking deployment criteria for {training_job_name}")
        
        try:
            # Get training job details
            training_job = self.sagemaker_client.describe_training_job(
                TrainingJobName=training_job_name
            )
            
            # Extract metrics from training job (if available)
            final_metrics = {}
            if 'FinalMetricDataList' in training_job:
                for metric in training_job['FinalMetricDataList']:
                    final_metrics[metric['MetricName']] = metric['Value']
            
            # Check if accuracy metric exists and meets threshold
            accuracy = final_metrics.get('accuracy', final_metrics.get('validation_accuracy', 0.0))
            
            evaluation_results = {
                'training_job_name': training_job_name,
                'accuracy': accuracy,
                'all_metrics': final_metrics,
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
            if accuracy >= self.config.ACCURACY_THRESHOLD:
                self.logger.info(f"✅ Model accuracy ({accuracy:.4f}) meets deployment threshold ({self.config.ACCURACY_THRESHOLD:.4f})")
                return True, evaluation_results
            elif accuracy >= self.config.MINIMUM_ACCURACY:
                self.logger.warning(f"⚠️ Model accuracy ({accuracy:.4f}) meets minimum but below optimal threshold")
                return False, evaluation_results
            else:
                self.logger.error(f"❌ Model accuracy ({accuracy:.4f}) below minimum threshold ({self.config.MINIMUM_ACCURACY:.4f})")
                return False, evaluation_results
                
        except Exception as e:
            self.logger.error(f"❌ Error checking deployment criteria: {str(e)}")
            evaluation_results = {
                'training_job_name': training_job_name,
                'error': str(e),
                'evaluation_timestamp': datetime.now().isoformat()
            }
            return False, evaluation_results
    
    def get_current_production_endpoint(self) -> Optional[str]:
        """Get the current production endpoint if it exists"""
        try:
            endpoints = self.sagemaker_client.list_endpoints(
                SortBy='CreationTime',
                SortOrder='Descending',
                MaxResults=10
            )
            
            for endpoint in endpoints['Endpoints']:
                if (endpoint['EndpointStatus'] == 'InService' and 
                    self.config.ENDPOINT_PREFIX in endpoint['EndpointName']):
                    self.logger.info(f"🎯 Found current production endpoint: {endpoint['EndpointName']}")
                    return endpoint['EndpointName']
                    
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error finding current endpoint: {str(e)}")
            return None
    
    def deploy_model(self, training_job_name: str, 
                    instance_type: str = None) -> Dict[str, Any]:
        """
        Deploy model from training job to SageMaker endpoint
        
        Args:
            training_job_name: Name of the completed training job
            instance_type: EC2 instance type for endpoint
            
        Returns:
            Deployment results dictionary
        """
        instance_type = instance_type or self.config.INSTANCE_TYPE
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        endpoint_name = f"{self.config.ENDPOINT_PREFIX}-{timestamp}"
        
        self.logger.info(f"🚀 Starting model deployment")
        self.logger.info(f"   Training Job: {training_job_name}")
        self.logger.info(f"   Endpoint Name: {endpoint_name}")
        self.logger.info(f"   Instance Type: {instance_type}")
        
        deployment_start_time = time.time()
        
        try:
            # Get training job details
            training_job = self.sagemaker_client.describe_training_job(
                TrainingJobName=training_job_name
            )
            
            model_data = training_job['ModelArtifacts']['S3ModelArtifacts']
            role_arn = training_job['RoleArn']
            
            # Initialize SageMaker session
            sagemaker_session = sagemaker.Session()
            
            # Create SKLearn model
            model = SKLearnModel(
                model_data=model_data,
                role=role_arn,
                entry_point='inference.py',
                framework_version='1.0-1',
                py_version='py3',
                sagemaker_session=sagemaker_session
            )
            
            # Store current endpoint for potential rollback
            self.previous_endpoint = self.get_current_production_endpoint()
            
            # Deploy the model
            self.logger.info("📦 Deploying model to endpoint...")
            predictor = model.deploy(
                initial_instance_count=1,
                instance_type=instance_type,
                endpoint_name=endpoint_name,
                wait=True
            )
            
            deployment_duration = time.time() - deployment_start_time
            
            # Test the deployed endpoint
            test_results = self._test_endpoint(endpoint_name)
            
            # Store deployment metadata
            self.deployment_metadata = {
                'endpoint_name': endpoint_name,
                'training_job_name': training_job_name,
                'instance_type': instance_type,
                'deployment_duration': deployment_duration,
                'deployment_timestamp': datetime.now().isoformat(),
                'previous_endpoint': self.previous_endpoint,
                'test_results': test_results
            }
            
            self.current_endpoint = endpoint_name
            
            deployment_results = {
                'status': 'success',
                'endpoint_name': endpoint_name,
                'deployment_duration': deployment_duration,
                'test_results': test_results,
                'metadata': self.deployment_metadata
            }
            
            self.logger.info(f"✅ Deployment successful in {deployment_duration:.2f} seconds")
            self.notification_manager.send_deployment_success_notification(deployment_results)
            
            return deployment_results
            
        except Exception as e:
            deployment_duration = time.time() - deployment_start_time
            error_message = str(e)
            
            self.logger.error(f"❌ Deployment failed after {deployment_duration:.2f} seconds: {error_message}")
            
            # Attempt rollback if enabled
            rollback_results = None
            if self.config.ROLLBACK_ON_FAILURE and self.previous_endpoint:
                rollback_results = self._rollback_deployment()
            
            deployment_results = {
                'status': 'failed',
                'error': error_message,
                'deployment_duration': deployment_duration,
                'rollback_results': rollback_results,
                'attempted_endpoint': endpoint_name
            }
            
            self.notification_manager.send_deployment_failure_notification(deployment_results)
            
            return deployment_results
    
    def _test_endpoint(self, endpoint_name: str) -> Dict[str, Any]:
        """Test the deployed endpoint with sample data"""
        self.logger.info(f"🧪 Testing endpoint: {endpoint_name}")
        
        try:
            runtime_client = boto3.client('sagemaker-runtime', 
                                        region_name=self.config.AWS_REGION)
            
            # Test with sample iris data
            test_data = [[5.1, 3.5, 1.4, 0.2], [7.0, 3.2, 4.7, 1.4], [6.3, 3.3, 6.0, 2.5]]
            
            test_start_time = time.time()
            
            response = runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(test_data)
            )
            
            test_duration = time.time() - test_start_time
            result = json.loads(response['Body'].read().decode())
            
            test_results = {
                'status': 'success',
                'test_duration_ms': test_duration * 1000,
                'predictions': result,
                'test_data': test_data
            }
            
            self.logger.info(f"✅ Endpoint test successful (latency: {test_duration*1000:.2f}ms)")
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"❌ Endpoint test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _rollback_deployment(self) -> Dict[str, Any]:
        """Rollback to previous endpoint if deployment fails"""
        if not self.previous_endpoint:
            self.logger.warning("⚠️ No previous endpoint available for rollback")
            return {'status': 'no_previous_endpoint'}
        
        self.logger.info(f"🔄 Rolling back to previous endpoint: {self.previous_endpoint}")
        
        try:
            # Check if previous endpoint is still available and healthy
            endpoint_desc = self.sagemaker_client.describe_endpoint(
                EndpointName=self.previous_endpoint
            )
            
            if endpoint_desc['EndpointStatus'] == 'InService':
                self.logger.info(f"✅ Rollback successful - using {self.previous_endpoint}")
                return {
                    'status': 'success',
                    'rolled_back_to': self.previous_endpoint
                }
            else:
                self.logger.error(f"❌ Previous endpoint {self.previous_endpoint} is not InService")
                return {
                    'status': 'failed',
                    'reason': f'Previous endpoint not available: {endpoint_desc["EndpointStatus"]}'
                }
                
        except Exception as e:
            self.logger.error(f"❌ Rollback failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def run_deployment_pipeline(self, training_job_name: str = None) -> Dict[str, Any]:
        """
        Execute the complete deployment pipeline with conditional deployment
        
        Args:
            training_job_name: Optional specific training job name
            
        Returns:
            Pipeline results including deployment decision and outcomes
        """
        pipeline_start_time = time.time()
        
        try:
            self.logger.info("🚀 Starting Enterprise MLOps Deployment Pipeline")
            
            # Step 1: Find training job if not provided
            if not training_job_name:
                training_job_name = self.get_latest_training_job()
                if not training_job_name:
                    raise ValueError("No suitable training job found")
            
            # Step 2: Check deployment criteria
            should_deploy, evaluation_results = self.check_deployment_criteria(training_job_name)
            
            # Step 3: Deploy if criteria met
            deployment_results = None
            if should_deploy and self.config.AUTO_DEPLOY_ENABLED:
                self.logger.info("✅ Deployment criteria met - proceeding with deployment")
                deployment_results = self.deploy_model(training_job_name)
            else:
                reason = "Deployment criteria not met" if not should_deploy else "Auto-deploy disabled"
                self.logger.info(f"⏸️ Skipping deployment: {reason}")
                
                # Send notification about skipped deployment
                skip_notification = {
                    'training_job_name': training_job_name,
                    'evaluation_results': evaluation_results,
                    'reason': reason
                }
                self.notification_manager.send_deployment_skipped_notification(skip_notification)
            
            pipeline_duration = time.time() - pipeline_start_time
            
            # Compile final results
            pipeline_results = {
                'pipeline_status': 'success',
                'pipeline_duration': pipeline_duration,
                'training_job_name': training_job_name,
                'should_deploy': should_deploy,
                'evaluation_results': evaluation_results,
                'deployment_results': deployment_results,
                'pipeline_timestamp': datetime.now().isoformat(),
                'config': self.config.to_dict()
            }
            
            self.logger.info(f"✅ Deployment pipeline completed in {pipeline_duration:.2f} seconds")
            
            return pipeline_results
            
        except Exception as e:
            pipeline_duration = time.time() - pipeline_start_time
            error_results = {
                'pipeline_status': 'failed',
                'pipeline_duration': pipeline_duration,
                'error': str(e),
                'pipeline_timestamp': datetime.now().isoformat()
            }
            
            self.logger.error(f"❌ Deployment pipeline failed: {str(e)}")
            self.notification_manager.send_error_notification(error_results)
            
            return error_results
