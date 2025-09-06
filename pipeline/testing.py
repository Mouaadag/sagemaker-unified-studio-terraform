#!/usr/bin/env python3
"""
Enterprise MLOps Testing Pipeline
Comprehensive testing suite for model validation and endpoint testing
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

try:
    import boto3
    import numpy as np
    from sklearn.metrics import (accuracy_score, classification_report,
                                 confusion_matrix)
except ImportError:
    print("Warning: Some testing dependencies not available")

from .config import PipelineConfig
from .notifications import NotificationManager


class TestingPipeline:
    """Enterprise-grade testing pipeline for ML models and endpoints"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = self._setup_logging()
        self.notification_manager = NotificationManager()
        self.sagemaker_client = boto3.client('sagemaker', region_name=self.config.AWS_REGION)
        self.runtime_client = boto3.client('sagemaker-runtime', region_name=self.config.AWS_REGION)
        
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
    
    def get_test_data(self) -> List[Dict[str, Any]]:
        """Get comprehensive test dataset for iris classification"""
        return [
            {
                "name": "Setosa Sample 1",
                "data": [5.1, 3.5, 1.4, 0.2],
                "expected_class": 0,
                "expected_species": "setosa"
            },
            {
                "name": "Setosa Sample 2", 
                "data": [4.9, 3.0, 1.4, 0.2],
                "expected_class": 0,
                "expected_species": "setosa"
            },
            {
                "name": "Versicolor Sample 1",
                "data": [7.0, 3.2, 4.7, 1.4],
                "expected_class": 1,
                "expected_species": "versicolor"
            },
            {
                "name": "Versicolor Sample 2",
                "data": [6.4, 3.2, 4.5, 1.5],
                "expected_class": 1,
                "expected_species": "versicolor"
            },
            {
                "name": "Virginica Sample 1",
                "data": [6.3, 3.3, 6.0, 2.5],
                "expected_class": 2,
                "expected_species": "virginica"
            },
            {
                "name": "Virginica Sample 2",
                "data": [5.8, 2.7, 5.1, 1.9],
                "expected_class": 2,
                "expected_species": "virginica"
            },
            # Edge cases
            {
                "name": "Boundary Case 1",
                "data": [6.0, 3.0, 4.0, 1.2],
                "expected_class": 1,  # Likely versicolor
                "expected_species": "versicolor"
            },
            {
                "name": "Boundary Case 2", 
                "data": [6.5, 3.0, 5.0, 1.8],
                "expected_class": 2,  # Likely virginica
                "expected_species": "virginica"
            }
        ]
    
    def test_endpoint_health(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Test endpoint health and availability
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            
        Returns:
            Health check results
        """
        self.logger.info(f"🏥 Testing endpoint health: {endpoint_name}")
        
        try:
            # Check endpoint status
            endpoint_desc = self.sagemaker_client.describe_endpoint(
                EndpointName=endpoint_name
            )
            
            status = endpoint_desc['EndpointStatus']
            creation_time = endpoint_desc['CreationTime']
            last_modified = endpoint_desc['LastModifiedTime']
            
            # Get instance information
            production_variants = endpoint_desc['ProductionVariants']
            instance_info = []
            
            for variant in production_variants:
                instance_info.append({
                    'variant_name': variant['VariantName'],
                    'instance_type': variant['InstanceType'],
                    'current_weight': variant['CurrentWeight'],
                    'desired_weight': variant['DesiredWeight'],
                    'current_instance_count': variant['CurrentInstanceCount'],
                    'desired_instance_count': variant['DesiredInstanceCount']
                })
            
            health_results = {
                'status': 'healthy' if status == 'InService' else 'unhealthy',
                'endpoint_status': status,
                'creation_time': creation_time.isoformat(),
                'last_modified_time': last_modified.isoformat(),
                'production_variants': instance_info,
                'health_check_timestamp': datetime.now().isoformat()
            }
            
            if status == 'InService':
                self.logger.info(f"✅ Endpoint is healthy and InService")
            else:
                self.logger.warning(f"⚠️ Endpoint status: {status}")
            
            return health_results
            
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'health_check_timestamp': datetime.now().isoformat()
            }
    
    def test_endpoint_predictions(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Test endpoint with comprehensive prediction scenarios
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            
        Returns:
            Prediction test results
        """
        self.logger.info(f"🧪 Testing endpoint predictions: {endpoint_name}")
        
        test_cases = self.get_test_data()
        prediction_results = []
        latencies = []
        correct_predictions = 0
        total_predictions = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            self.logger.info(f"  Testing case {i}/{total_predictions}: {test_case['name']}")
            
            try:
                # Measure latency
                start_time = time.time()
                
                response = self.runtime_client.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps([test_case['data']])
                )
                
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                # Parse prediction
                result = json.loads(response['Body'].read().decode())
                predicted_class = result[0] if isinstance(result, list) else result
                
                # Check correctness
                is_correct = predicted_class == test_case['expected_class']
                if is_correct:
                    correct_predictions += 1
                
                test_result = {
                    'test_name': test_case['name'],
                    'input_data': test_case['data'],
                    'expected_class': test_case['expected_class'],
                    'expected_species': test_case['expected_species'],
                    'predicted_class': predicted_class,
                    'is_correct': is_correct,
                    'latency_ms': latency_ms,
                    'status': 'success'
                }
                
                prediction_results.append(test_result)
                
                if is_correct:
                    self.logger.info(f"    ✅ Correct prediction: {predicted_class}")
                else:
                    self.logger.warning(f"    ⚠️ Incorrect prediction: {predicted_class} (expected: {test_case['expected_class']})")
                
            except Exception as e:
                self.logger.error(f"    ❌ Prediction failed: {str(e)}")
                prediction_results.append({
                    'test_name': test_case['name'],
                    'input_data': test_case['data'],
                    'expected_class': test_case['expected_class'],
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Calculate statistics
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        
        prediction_test_results = {
            'accuracy': accuracy,
            'correct_predictions': correct_predictions,
            'total_predictions': total_predictions,
            'avg_latency_ms': avg_latency,
            'max_latency_ms': max_latency,
            'min_latency_ms': min_latency,
            'individual_results': prediction_results,
            'test_timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"📊 Prediction test summary:")
        self.logger.info(f"   Accuracy: {accuracy:.2%}")
        self.logger.info(f"   Average latency: {avg_latency:.2f}ms")
        self.logger.info(f"   Correct predictions: {correct_predictions}/{total_predictions}")
        
        return prediction_test_results
    
    def test_endpoint_performance(self, endpoint_name: str, 
                                 num_concurrent_requests: int = 10,
                                 duration_seconds: int = 30) -> Dict[str, Any]:
        """
        Test endpoint performance under load
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            num_concurrent_requests: Number of concurrent requests
            duration_seconds: Duration of the test in seconds
            
        Returns:
            Performance test results
        """
        self.logger.info(f"⚡ Testing endpoint performance: {endpoint_name}")
        self.logger.info(f"   Concurrent requests: {num_concurrent_requests}")
        self.logger.info(f"   Duration: {duration_seconds} seconds")
        
        # Simple performance test (sequential for now)
        test_data = [5.1, 3.5, 1.4, 0.2]  # Standard test sample
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_times = []
        successful_requests = 0
        failed_requests = 0
        
        while time.time() < end_time:
            try:
                request_start = time.time()
                
                response = self.runtime_client.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps([test_data])
                )
                
                request_end = time.time()
                request_time = (request_end - request_start) * 1000  # ms
                request_times.append(request_time)
                successful_requests += 1
                
            except Exception as e:
                failed_requests += 1
                self.logger.warning(f"Request failed: {str(e)}")
            
            # Small delay to prevent overwhelming the endpoint
            time.sleep(0.1)
        
        total_duration = time.time() - start_time
        total_requests = successful_requests + failed_requests
        
        # Calculate statistics
        if request_times:
            avg_latency = sum(request_times) / len(request_times)
            max_latency = max(request_times)
            min_latency = min(request_times)
            p95_latency = sorted(request_times)[int(0.95 * len(request_times))] if len(request_times) > 0 else 0
        else:
            avg_latency = max_latency = min_latency = p95_latency = 0
        
        throughput = successful_requests / total_duration if total_duration > 0 else 0
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        performance_results = {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': success_rate,
            'throughput_rps': throughput,
            'avg_latency_ms': avg_latency,
            'max_latency_ms': max_latency,
            'min_latency_ms': min_latency,
            'p95_latency_ms': p95_latency,
            'test_duration_seconds': total_duration,
            'performance_test_timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"📈 Performance test results:")
        self.logger.info(f"   Success rate: {success_rate:.2%}")
        self.logger.info(f"   Throughput: {throughput:.2f} requests/second")
        self.logger.info(f"   Average latency: {avg_latency:.2f}ms")
        self.logger.info(f"   P95 latency: {p95_latency:.2f}ms")
        
        return performance_results
    
    def run_comprehensive_tests(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Run comprehensive test suite on endpoint
        
        Args:
            endpoint_name: Name of the SageMaker endpoint
            
        Returns:
            Complete test results
        """
        test_start_time = time.time()
        
        self.logger.info(f"🧪 Starting comprehensive test suite for {endpoint_name}")
        
        try:
            # Test 1: Health Check
            self.logger.info("🏥 Running health check...")
            health_results = self.test_endpoint_health(endpoint_name)
            
            # Test 2: Prediction Accuracy
            self.logger.info("🎯 Running prediction tests...")
            prediction_results = self.test_endpoint_predictions(endpoint_name)
            
            # Test 3: Performance Testing
            self.logger.info("⚡ Running performance tests...")
            performance_results = self.test_endpoint_performance(endpoint_name)
            
            test_duration = time.time() - test_start_time
            
            # Determine overall test status
            overall_status = 'passed'
            issues = []
            
            # Check health
            if health_results.get('status') != 'healthy':
                overall_status = 'failed'
                issues.append('Endpoint health check failed')
            
            # Check prediction accuracy
            prediction_accuracy = prediction_results.get('accuracy', 0.0)
            if prediction_accuracy < self.config.MINIMUM_ACCURACY:
                overall_status = 'failed'
                issues.append(f'Prediction accuracy ({prediction_accuracy:.2%}) below minimum threshold')
            
            # Check performance
            success_rate = performance_results.get('success_rate', 0.0)
            if success_rate < 0.95:  # 95% success rate minimum
                overall_status = 'warning'
                issues.append(f'Performance test success rate ({success_rate:.2%}) below 95%')
            
            avg_latency = performance_results.get('avg_latency_ms', 0.0)
            if avg_latency > 1000:  # 1 second maximum
                overall_status = 'warning'
                issues.append(f'Average latency ({avg_latency:.2f}ms) above 1 second')
            
            comprehensive_results = {
                'overall_status': overall_status,
                'test_duration_seconds': test_duration,
                'health_results': health_results,
                'prediction_results': prediction_results,
                'performance_results': performance_results,
                'issues': issues,
                'endpoint_name': endpoint_name,
                'test_timestamp': datetime.now().isoformat(),
                'test_summary': {
                    'health_status': health_results.get('status'),
                    'prediction_accuracy': prediction_accuracy,
                    'performance_success_rate': success_rate,
                    'avg_latency_ms': avg_latency
                }
            }
            
            # Send notification based on results
            if overall_status == 'passed':
                self.logger.info(f"✅ All tests passed for {endpoint_name}")
            elif overall_status == 'warning':
                self.logger.warning(f"⚠️ Tests completed with warnings for {endpoint_name}")
            else:
                self.logger.error(f"❌ Tests failed for {endpoint_name}")
            
            self.logger.info(f"🏁 Comprehensive testing completed in {test_duration:.2f} seconds")
            
            return comprehensive_results
            
        except Exception as e:
            test_duration = time.time() - test_start_time
            error_results = {
                'overall_status': 'error',
                'test_duration_seconds': test_duration,
                'error': str(e),
                'endpoint_name': endpoint_name,
                'test_timestamp': datetime.now().isoformat()
            }
            
            self.logger.error(f"❌ Comprehensive testing failed: {str(e)}")
            
            return error_results
