#!/usr/bin/env python3
"""
MLOps-grade model deployment script using SageMaker SDK.
This script can be called from CI/CD pipelines, shell scripts, or automation.
"""

import argparse
import json
import sys
from datetime import datetime

import boto3
from sagemaker import get_execution_role
from sagemaker.sklearn.model import SKLearnModel


def get_latest_training_job(region='us-east-1'):
    """Find the most recent completed training job."""
    sagemaker_client = boto3.client('sagemaker', region_name=region)
    
    # Look for iris training jobs first
    response = sagemaker_client.list_training_jobs(
        SortBy='CreationTime',
        SortOrder='Descending',
        MaxResults=10
    )
    
    for job in response['TrainingJobs']:
        if (job['TrainingJobStatus'] == 'Completed' and 
            'iris' in job['TrainingJobName'].lower()):
            return job['TrainingJobName']
    
    # Fallback to any completed training job
    for job in response['TrainingJobs']:
        if job['TrainingJobStatus'] == 'Completed':
            return job['TrainingJobName']
    
    return None


def deploy_model(training_job_name, region='us-east-1', instance_type='ml.m5.large'):
    """Deploy a model from a training job using SageMaker SDK."""
    
    print(f"🚀 Deploying model from training job: {training_job_name}")
    
    # Initialize SageMaker session
    import sagemaker
    sagemaker_session = sagemaker.Session(boto3.Session(region_name=region))
    
    # Get execution role
    try:
        role = get_execution_role()
        print(f"✅ Using execution role: {role}")
    except Exception:
        # Fallback to finding role from training job
        sagemaker_client = boto3.client('sagemaker', region_name=region)
        training_job = sagemaker_client.describe_training_job(TrainingJobName=training_job_name)
        role = training_job['RoleArn']
        print(f"✅ Using role from training job: {role}")
    
    # Get model artifacts from training job
    sagemaker_client = boto3.client('sagemaker', region_name=region)
    training_job = sagemaker_client.describe_training_job(TrainingJobName=training_job_name)
    
    model_data = training_job['ModelArtifacts']['S3ModelArtifacts']
    image_uri = training_job['AlgorithmSpecification']['TrainingImage']
    
    print(f"📦 Model artifacts: {model_data}")
    print(f"🐳 Container image: {image_uri}")
    
    # Create SKLearn model (this handles inference properly)
    model = SKLearnModel(
        model_data=model_data,
        role=role,
        entry_point='inference.py',  # This will be in the model.tar.gz
        framework_version='1.0-1',
        py_version='py3',
        sagemaker_session=sagemaker_session
    )
    
    # Generate endpoint name
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    endpoint_name = f'iris-model-{timestamp}'
    
    print(f"🎯 Deploying to endpoint: {endpoint_name}")
    print(f"⚙️ Instance type: {instance_type}")
    print(f"📍 Region: {region}")
    
    # Deploy the model
    try:
        predictor = model.deploy(
            initial_instance_count=1,
            instance_type=instance_type,
            endpoint_name=endpoint_name
        )
        
        print(f"✅ Deployment successful!")
        print(f"📍 Endpoint name: {endpoint_name}")
        
        # Test the endpoint
        print("\n🧪 Testing the endpoint...")
        test_data = [[5.1, 3.5, 1.4, 0.2]]
        
        try:
            prediction = predictor.predict(test_data)
            print(f"🎯 Test prediction: {prediction}")
            print("✅ Endpoint is working correctly!")
            
            return {
                'endpoint_name': endpoint_name,
                'status': 'success',
                'test_prediction': prediction
            }
            
        except Exception as e:
            print(f"⚠️ Endpoint deployed but test failed: {e}")
            return {
                'endpoint_name': endpoint_name,
                'status': 'deployed_but_test_failed',
                'error': str(e)
            }
            
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Deploy SageMaker model')
    parser.add_argument('--training-job', help='Training job name to deploy')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--instance-type', default='ml.m5.large', help='Instance type')
    parser.add_argument('--output-json', help='Output deployment info to JSON file')
    
    args = parser.parse_args()
    
    # Find training job if not specified
    training_job_name = args.training_job
    if not training_job_name:
        print("🔍 Finding latest training job...")
        training_job_name = get_latest_training_job(args.region)
        if not training_job_name:
            print("❌ No completed training jobs found")
            sys.exit(1)
    
    # Deploy the model
    result = deploy_model(
        training_job_name=training_job_name,
        region=args.region,
        instance_type=args.instance_type
    )
    
    # Output results
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"📄 Results written to: {args.output_json}")
    
    # Exit with appropriate code
    if result['status'] == 'success':
        print("\n🎉 Deployment completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Deployment failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
