#!/usr/bin/env python3
"""
Complete MLOps Pipeline Orchestrator
Runs the full pipeline: Training → Deployment → Testing → Notifications
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict

from pipeline.config import PipelineConfig
from pipeline.deployment import DeploymentPipeline
from pipeline.testing import TestingPipeline
# Import pipeline components
from pipeline.training import TrainingPipeline


def main():
    parser = argparse.ArgumentParser(description='Run complete MLOps pipeline')
    parser.add_argument('--role-arn', required=True, 
                       help='SageMaker execution role ARN')
    parser.add_argument('--mode', default='complete',
                       choices=['complete', 'training', 'deployment', 'testing'],
                       help='Pipeline mode to run')
    parser.add_argument('--training-job', 
                       help='Specific training job name for deployment mode')
    parser.add_argument('--endpoint-name',
                       help='Specific endpoint name for testing mode')
    parser.add_argument('--output-file', 
                       help='Output results to JSON file')
    parser.add_argument('--config-file',
                       help='Custom configuration file')
    parser.add_argument('--accuracy-threshold', type=float,
                       help='Override accuracy threshold')
    parser.add_argument('--minimum-accuracy', type=float,
                       help='Override minimum accuracy')
    parser.add_argument('--instance-type',
                       help='Override SageMaker instance type')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup configuration
    config = PipelineConfig()
    
    # Override configuration with command line arguments
    if args.accuracy_threshold:
        config.ACCURACY_THRESHOLD = args.accuracy_threshold
    if args.minimum_accuracy:
        config.MINIMUM_ACCURACY = args.minimum_accuracy
    if args.instance_type:
        config.INSTANCE_TYPE = args.instance_type
    
    if args.verbose:
        config.LOG_LEVEL = 'DEBUG'
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    print("🚀 Starting MLOps Pipeline")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Role ARN: {args.role_arn}")
    print(f"Accuracy Threshold: {config.ACCURACY_THRESHOLD}")
    print(f"Minimum Accuracy: {config.MINIMUM_ACCURACY}")
    print(f"Instance Type: {config.INSTANCE_TYPE}")
    print("=" * 60)
    
    pipeline_start_time = time.time()
    results = {}
    
    try:
        if args.mode in ['complete', 'training']:
            print("\n🎯 Starting Training Phase...")
            trainer = TrainingPipeline(config)
            train_results = trainer.run_training_pipeline(args.role_arn)
            results['training'] = train_results
            
            print(f"\n📊 Training Results:")
            print(f"   Status: {train_results['pipeline_status']}")
            print(f"   Accuracy: {train_results['evaluation_results']['accuracy']:.4f}")
            print(f"   Should Deploy: {train_results['should_deploy']}")
            print(f"   Duration: {train_results['pipeline_duration']:.2f}s")
            
            if args.mode == 'training':
                print("\n✅ Training phase completed")
                
        if args.mode in ['complete', 'deployment']:
            print("\n🚀 Starting Deployment Phase...")
            deployer = DeploymentPipeline(config)
            
            if args.mode == 'deployment' and args.training_job:
                deploy_results = deployer.run_deployment_pipeline(args.training_job)
            elif args.mode == 'complete' and results.get('training', {}).get('should_deploy'):
                deploy_results = deployer.run_deployment_pipeline()
            elif args.mode == 'deployment':
                deploy_results = deployer.run_deployment_pipeline()
            else:
                print("⏸️ Skipping deployment - criteria not met or not applicable")
                deploy_results = {'pipeline_status': 'skipped', 'reason': 'deployment criteria not met'}
            
            results['deployment'] = deploy_results
            
            print(f"\n📦 Deployment Results:")
            print(f"   Status: {deploy_results['pipeline_status']}")
            if deploy_results.get('deployment_results'):
                endpoint_name = deploy_results['deployment_results']['endpoint_name']
                print(f"   Endpoint: {endpoint_name}")
                print(f"   Duration: {deploy_results['deployment_results']['deployment_duration']:.2f}s")
            
            if args.mode == 'deployment':
                print("\n✅ Deployment phase completed")
                
        if args.mode in ['complete', 'testing']:
            print("\n🧪 Starting Testing Phase...")
            tester = TestingPipeline(config)
            
            # Determine endpoint name
            endpoint_name = None
            if args.endpoint_name:
                endpoint_name = args.endpoint_name
            elif results.get('deployment', {}).get('deployment_results'):
                endpoint_name = results['deployment']['deployment_results']['endpoint_name']
            else:
                # Try to find latest endpoint
                import boto3
                sagemaker_client = boto3.client('sagemaker', region_name=config.AWS_REGION)
                response = sagemaker_client.list_endpoints(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=5
                )
                
                for endpoint in response['Endpoints']:
                    if (endpoint['EndpointStatus'] == 'InService' and 
                        config.ENDPOINT_PREFIX in endpoint['EndpointName']):
                        endpoint_name = endpoint['EndpointName']
                        break
            
            if endpoint_name:
                test_results = tester.run_comprehensive_tests(endpoint_name)
                results['testing'] = test_results
                
                print(f"\n🔬 Testing Results:")
                print(f"   Overall Status: {test_results['overall_status']}")
                print(f"   Health: {test_results['health_results']['status']}")
                print(f"   Accuracy: {test_results['prediction_results']['accuracy']:.2%}")
                print(f"   Avg Latency: {test_results['performance_results']['avg_latency_ms']:.2f}ms")
                print(f"   Success Rate: {test_results['performance_results']['success_rate']:.2%}")
            else:
                print("⚠️ No endpoint available for testing")
                results['testing'] = {'status': 'skipped', 'reason': 'no endpoint available'}
            
            if args.mode == 'testing':
                print("\n✅ Testing phase completed")
        
        pipeline_duration = time.time() - pipeline_start_time
        
        # Final results summary
        results['pipeline_summary'] = {
            'status': 'success',
            'mode': args.mode,
            'total_duration': pipeline_duration,
            'timestamp': datetime.now().isoformat(),
            'config': config.to_dict()
        }
        
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Total Duration: {pipeline_duration:.2f} seconds")
        
        if args.mode == 'complete':
            training_status = results.get('training', {}).get('pipeline_status', 'not_run')
            deployment_status = results.get('deployment', {}).get('pipeline_status', 'not_run')
            testing_status = results.get('testing', {}).get('overall_status', 'not_run')
            
            print(f"Training: {training_status}")
            print(f"Deployment: {deployment_status}")
            print(f"Testing: {testing_status}")
        
        # Output to file if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📄 Results saved to: {args.output_file}")
        
        return 0
        
    except Exception as e:
        pipeline_duration = time.time() - pipeline_start_time
        
        error_results = {
            'pipeline_summary': {
                'status': 'failed',
                'mode': args.mode,
                'error': str(e),
                'total_duration': pipeline_duration,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        print("\n" + "=" * 60)
        print("❌ PIPELINE FAILED")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print(f"Duration: {pipeline_duration:.2f} seconds")
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(error_results, f, indent=2, default=str)
            print(f"\n📄 Error details saved to: {args.output_file}")
        
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
    sys.exit(exit_code)
