#!/usr/bin/env python3
"""
Enterprise MLOps Training Pipeline
Handles model training with proper logging, monitoring, and evaluation
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import boto3
import joblib
import numpy as np
import pandas as pd
import sagemaker
from sagemaker.sklearn.estimator import SKLearn
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix)
from sklearn.model_selection import cross_val_score, train_test_split

from .config import PipelineConfig
from .notifications import NotificationManager


class TrainingPipeline:
    """Enterprise-grade training pipeline for ML models"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = self._setup_logging()
        self.sagemaker_session = sagemaker.Session()
        self.notification_manager = NotificationManager()
        
        # Training metrics
        self.training_job_name = None
        self.model_artifacts_s3_path = None
        self.training_metrics = {}
        
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
    
    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare and split the iris dataset for training
        
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        self.logger.info("🔄 Preparing iris dataset for training")
        
        # Load iris dataset
        iris = load_iris()
        X, y = iris.data, iris.target
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        self.logger.info(f"✅ Data prepared: {X_train.shape[0]} training samples, {X_test.shape[0]} test samples")
        
        # Log class distribution
        unique, counts = np.unique(y_train, return_counts=True)
        class_dist = dict(zip(unique, counts))
        self.logger.info(f"📊 Training class distribution: {class_dist}")
        
        return X_train, X_test, y_train, y_test
    
    def train_local_model(self, X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
        """
        Train a local model for validation
        
        Args:
            X_train: Training features
            y_train: Training labels
            
        Returns:
            Trained RandomForest model
        """
        self.logger.info("🎯 Training local RandomForest model for validation")
        
        # Create and train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        self.logger.info(f"✅ Local model training completed in {training_time:.2f} seconds")
        
        return model
    
    def evaluate_model(self, model: RandomForestClassifier, 
                      X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """
        Comprehensive model evaluation
        
        Args:
            model: Trained model
            X_test: Test features  
            y_test: Test labels
            
        Returns:
            Dictionary containing evaluation metrics
        """
        self.logger.info("📊 Evaluating model performance")
        
        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        
        # Cross-validation score
        cv_scores = cross_val_score(model, X_test, y_test, cv=5)
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
        
        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        # Confusion matrix
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        # Feature importance
        feature_importance = model.feature_importances_.tolist()
        
        evaluation_results = {
            'accuracy': float(accuracy),
            'cv_mean_accuracy': float(cv_mean),
            'cv_std_accuracy': float(cv_std),
            'classification_report': class_report,
            'confusion_matrix': conf_matrix.tolist(),
            'feature_importance': feature_importance,
            'test_samples': len(y_test),
            'evaluation_timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"📈 Model Accuracy: {accuracy:.4f}")
        self.logger.info(f"📈 CV Mean Accuracy: {cv_mean:.4f} (±{cv_std:.4f})")
        
        # Store metrics for pipeline decision
        self.training_metrics = evaluation_results
        
        return evaluation_results
    
    def train_sagemaker_model(self, role_arn: str) -> str:
        """
        Train model using SageMaker training job
        
        Args:
            role_arn: IAM role ARN for SageMaker
            
        Returns:
            Training job name
        """
        self.logger.info("🚀 Starting SageMaker training job")
        
        # Create training script
        training_script = self._create_training_script()
        
        # Create SKLearn estimator
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.training_job_name = f"{self.config.MODEL_NAME_PREFIX}-{timestamp}"
        
        sklearn_estimator = SKLearn(
            entry_point='train.py',
            role=role_arn,
            instance_type='ml.m5.large',
            framework_version='1.0-1',
            py_version='py3',
            hyperparameters={
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42
            },
            output_path=f's3://{self.config.S3_BUCKET}/{self.config.MODEL_ARTIFACTS_PREFIX}/',
            code_location=f's3://{self.config.S3_BUCKET}/code/',
            base_job_name=self.config.MODEL_NAME_PREFIX
        )
        
        self.logger.info(f"📝 Training job name: {self.training_job_name}")
        
        # Start training
        try:
            sklearn_estimator.fit()
            self.model_artifacts_s3_path = sklearn_estimator.model_data
            self.logger.info(f"✅ Training job completed successfully")
            self.logger.info(f"📦 Model artifacts: {self.model_artifacts_s3_path}")
            
            return self.training_job_name
            
        except Exception as e:
            self.logger.error(f"❌ Training job failed: {str(e)}")
            raise
    
    def _create_training_script(self) -> str:
        """Create the training script for SageMaker"""
        training_script = '''
import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os

def model_fn(model_dir):
    """Load model for inference"""
    model = joblib.load(os.path.join(model_dir, "model.joblib"))
    return model

def train():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=100)
    parser.add_argument("--max_depth", type=int, default=10)
    parser.add_argument("--random_state", type=int, default=42)
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR"))
    
    args = parser.parse_args()
    
    # Load and prepare data
    iris = load_iris()
    X, y = iris.data, iris.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model accuracy: {accuracy:.4f}")
    
    # Save model
    joblib.dump(model, os.path.join(args.model_dir, "model.joblib"))

if __name__ == "__main__":
    train()
'''
        
        # Write training script to file
        script_path = '/tmp/train.py'
        with open(script_path, 'w') as f:
            f.write(training_script)
            
        return script_path
    
    def should_deploy(self, evaluation_results: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if model should be deployed based on accuracy threshold
        
        Args:
            evaluation_results: Model evaluation metrics
            
        Returns:
            Tuple of (should_deploy: bool, reason: str)
        """
        accuracy = evaluation_results['accuracy']
        cv_accuracy = evaluation_results['cv_mean_accuracy']
        
        self.logger.info(f"🎯 Checking deployment criteria:")
        self.logger.info(f"   Model Accuracy: {accuracy:.4f}")
        self.logger.info(f"   CV Accuracy: {cv_accuracy:.4f}")
        self.logger.info(f"   Required Threshold: {self.config.ACCURACY_THRESHOLD:.4f}")
        self.logger.info(f"   Minimum Threshold: {self.config.MINIMUM_ACCURACY:.4f}")
        
        if accuracy >= self.config.ACCURACY_THRESHOLD:
            reason = f"✅ Model accuracy ({accuracy:.4f}) meets deployment threshold ({self.config.ACCURACY_THRESHOLD:.4f})"
            self.logger.info(reason)
            return True, reason
            
        elif accuracy >= self.config.MINIMUM_ACCURACY:
            reason = f"⚠️ Model accuracy ({accuracy:.4f}) meets minimum threshold ({self.config.MINIMUM_ACCURACY:.4f}) but below optimal ({self.config.ACCURACY_THRESHOLD:.4f})"
            self.logger.warning(reason)
            return False, reason
            
        else:
            reason = f"❌ Model accuracy ({accuracy:.4f}) below minimum threshold ({self.config.MINIMUM_ACCURACY:.4f})"
            self.logger.error(reason)
            return False, reason
    
    def run_training_pipeline(self, role_arn: str) -> Dict[str, Any]:
        """
        Execute the complete training pipeline
        
        Args:
            role_arn: IAM role ARN for SageMaker
            
        Returns:
            Pipeline results including metrics and deployment decision
        """
        pipeline_start_time = time.time()
        
        try:
            self.logger.info("🚀 Starting Enterprise MLOps Training Pipeline")
            
            # Step 1: Prepare data
            X_train, X_test, y_train, y_test = self.prepare_data()
            
            # Step 2: Train local model for validation
            local_model = self.train_local_model(X_train, y_train)
            
            # Step 3: Evaluate model
            evaluation_results = self.evaluate_model(local_model, X_test, y_test)
            
            # Step 4: Determine deployment eligibility
            should_deploy, deployment_reason = self.should_deploy(evaluation_results)
            
            # Step 5: Train SageMaker model if deployment criteria met
            sagemaker_training_job = None
            if should_deploy and self.config.AUTO_DEPLOY_ENABLED:
                self.logger.info("🎯 Model meets criteria, starting SageMaker training")
                sagemaker_training_job = self.train_sagemaker_model(role_arn)
            else:
                self.logger.info("⏸️ Skipping SageMaker training - deployment criteria not met or auto-deploy disabled")
            
            pipeline_duration = time.time() - pipeline_start_time
            
            # Compile pipeline results
            pipeline_results = {
                'pipeline_status': 'success',
                'pipeline_duration': pipeline_duration,
                'evaluation_results': evaluation_results,
                'should_deploy': should_deploy,
                'deployment_reason': deployment_reason,
                'sagemaker_training_job': sagemaker_training_job,
                'model_artifacts_s3_path': self.model_artifacts_s3_path,
                'pipeline_timestamp': datetime.now().isoformat(),
                'config': self.config.to_dict()
            }
            
            # Send notifications
            if should_deploy:
                self.notification_manager.send_success_notification(pipeline_results)
            else:
                self.notification_manager.send_failure_notification(pipeline_results)
            
            self.logger.info(f"✅ Training pipeline completed in {pipeline_duration:.2f} seconds")
            
            return pipeline_results
            
        except Exception as e:
            pipeline_duration = time.time() - pipeline_start_time
            error_results = {
                'pipeline_status': 'failed',
                'pipeline_duration': pipeline_duration,
                'error': str(e),
                'pipeline_timestamp': datetime.now().isoformat()
            }
            
            self.logger.error(f"❌ Training pipeline failed: {str(e)}")
            self.notification_manager.send_error_notification(error_results)
            
            raise
