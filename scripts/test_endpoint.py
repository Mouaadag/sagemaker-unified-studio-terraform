#!/usr/bin/env python3
"""
Test script for the deployed SageMaker endpoint.
This script demonstrates how to make predictions using the iris classifier.
"""

import argparse
import json
import sys
from typing import Any, Dict, List

import boto3


def test_endpoint(endpoint_name: str, region: str = 'us-east-1') -> None:
    """Test the SageMaker endpoint with sample data."""
    
    print(f"Testing SageMaker endpoint: {endpoint_name}")
    print(f"Region: {region}")
    
    # Initialize SageMaker runtime client
    try:
        runtime = boto3.client('sagemaker-runtime', region_name=region)
        print("✅ Successfully connected to SageMaker runtime")
    except Exception as e:
        print(f"❌ Failed to connect to SageMaker runtime: {e}")
        return
    
    # Test cases for iris dataset
    test_cases = [
        {
            "name": "Setosa (should predict 'setosa')",
            "data": [[5.1, 3.5, 1.4, 0.2]],
            "expected": "setosa"
        },
        {
            "name": "Versicolor (should predict 'versicolor')",
            "data": [[7.0, 3.2, 4.7, 1.4]],
            "expected": "versicolor"
        },
        {
            "name": "Virginica (should predict 'virginica')",
            "data": [[6.3, 3.3, 6.0, 2.5]],
            "expected": "virginica"
        },
        {
            "name": "Batch prediction (multiple samples)",
            "data": [
                [5.1, 3.5, 1.4, 0.2],  # setosa
                [7.0, 3.2, 4.7, 1.4],  # versicolor
                [6.3, 3.3, 6.0, 2.5]   # virginica
            ],
            "expected": ["setosa", "versicolor", "virginica"]
        }
    ]
    
    print("\n" + "="*60)
    print("RUNNING ENDPOINT TESTS")
    print("="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Input: {test_case['data']}")
        
        try:
            # Make prediction
            response = runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(test_case['data'])
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            predictions = result.get('predictions', [])
            probabilities = result.get('probabilities', {})
            
            print(f"✅ Predictions: {predictions}")
            
            if probabilities:
                print("📊 Probabilities:")
                for class_name, probs in probabilities.items():
                    if isinstance(probs, list) and len(probs) > 0:
                        print(f"   {class_name}: {probs[0]:.4f}")
            
            # Check if prediction matches expected (for single predictions)
            if len(predictions) == 1 and isinstance(test_case['expected'], str):
                if predictions[0] == test_case['expected']:
                    print(f"✅ Correct prediction!")
                else:
                    print(f"⚠️  Expected {test_case['expected']}, got {predictions[0]}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            continue
    
    print("\n" + "="*60)
    print("ENDPOINT HEALTH CHECK")
    print("="*60)
    
    # Check endpoint status
    try:
        sagemaker = boto3.client('sagemaker', region_name=region)
        endpoint_info = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        
        status = endpoint_info['EndpointStatus']
        instance_type = endpoint_info['ProductionVariants'][0]['InstanceType']
        current_weight = endpoint_info['ProductionVariants'][0]['CurrentWeight']
        
        print(f"Endpoint Status: {status}")
        print(f"Instance Type: {instance_type}")
        print(f"Current Weight: {current_weight}")
        
        if status == 'InService':
            print("✅ Endpoint is healthy and ready for production!")
        else:
            print(f"⚠️  Endpoint status is {status}")
            
    except Exception as e:
        print(f"❌ Failed to get endpoint status: {e}")

def main():
    """Main function to run endpoint tests."""
    parser = argparse.ArgumentParser(description='Test SageMaker endpoint')
    parser.add_argument('--endpoint-name', required=True, help='Name of the SageMaker endpoint')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    print("🧪 SageMaker Endpoint Test Suite")
    print("="*60)
    
    test_endpoint(args.endpoint_name, args.region)

if __name__ == '__main__':
    main()
