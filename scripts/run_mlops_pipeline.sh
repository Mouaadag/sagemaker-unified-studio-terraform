#!/bin/bash
# MLOps Pipeline Runner Script
# Provides easy command-line interface for running the complete pipeline

set -e  # Exit on any error

# Default values
MODE="complete"
REGION="us-east-1"
ACCURACY_THRESHOLD=""
MINIMUM_ACCURACY=""
INSTANCE_TYPE=""
ROLE_ARN=""
TRAINING_JOB=""
ENDPOINT_NAME=""
OUTPUT_FILE=""
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
🚀 MLOps Pipeline Runner

Usage: $0 [OPTIONS]

Required:
  --role-arn ARN                SageMaker execution role ARN

Options:
  --mode MODE                   Pipeline mode: complete|training|deployment|testing (default: complete)
  --region REGION               AWS region (default: us-east-1)
  --accuracy THRESHOLD          Accuracy threshold for deployment (0.0-1.0)
  --minimum-accuracy THRESHOLD  Minimum acceptable accuracy (0.0-1.0)
  --instance-type TYPE          SageMaker instance type (e.g., ml.m5.large)
  --training-job NAME           Specific training job for deployment mode
  --endpoint-name NAME          Specific endpoint for testing mode
  --output-file FILE            Save results to JSON file
  --verbose                     Enable verbose logging
  --help                        Show this help message

Examples:
  # Run complete pipeline
  $0 --role-arn arn:aws:iam::123456789012:role/SageMakerRole

  # Run with custom accuracy threshold
  $0 --role-arn arn:aws:iam::123456789012:role/SageMakerRole --accuracy 0.98

  # Run only training
  $0 --role-arn arn:aws:iam::123456789012:role/SageMakerRole --mode training

  # Deploy specific training job
  $0 --mode deployment --training-job iris-classifier-20250906-123456

  # Test specific endpoint
  $0 --mode testing --endpoint-name iris-model-20250906-123456

Environment Variables:
  ACCURACY_THRESHOLD            Override accuracy threshold
  MINIMUM_ACCURACY              Override minimum accuracy
  AWS_REGION                    Override AWS region
  INSTANCE_TYPE                 Override instance type
  AUTO_DEPLOY_ENABLED           Enable/disable auto-deployment
  ROLLBACK_ON_FAILURE          Enable/disable rollback
  SNS_TOPIC_ARN                SNS topic for notifications
  SLACK_WEBHOOK_URL            Slack webhook URL
  LOG_LEVEL                     Logging level (DEBUG, INFO, WARNING, ERROR)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --role-arn)
            ROLE_ARN="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --accuracy)
            ACCURACY_THRESHOLD="$2"
            shift 2
            ;;
        --minimum-accuracy)
            MINIMUM_ACCURACY="$2"
            shift 2
            ;;
        --instance-type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        --training-job)
            TRAINING_JOB="$2"
            shift 2
            ;;
        --endpoint-name)
            ENDPOINT_NAME="$2"
            shift 2
            ;;
        --output-file)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ROLE_ARN" && "$MODE" != "testing" ]]; then
    echo -e "${RED}❌ Error: --role-arn is required for training and deployment modes${NC}"
    show_help
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "run_pipeline.py" ]]; then
    echo -e "${RED}❌ Error: run_pipeline.py not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Check if pipeline module exists
if [[ ! -d "pipeline" ]]; then
    echo -e "${RED}❌ Error: pipeline directory not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Set environment variables
export AWS_REGION="${REGION}"

echo -e "${BLUE}🚀 MLOps Pipeline Runner${NC}"
echo "=================================="
echo "Mode: $MODE"
echo "Region: $REGION"
[[ -n "$ROLE_ARN" ]] && echo "Role ARN: $ROLE_ARN"
[[ -n "$ACCURACY_THRESHOLD" ]] && echo "Accuracy Threshold: $ACCURACY_THRESHOLD"
[[ -n "$MINIMUM_ACCURACY" ]] && echo "Minimum Accuracy: $MINIMUM_ACCURACY"
[[ -n "$INSTANCE_TYPE" ]] && echo "Instance Type: $INSTANCE_TYPE"
[[ -n "$TRAINING_JOB" ]] && echo "Training Job: $TRAINING_JOB"
[[ -n "$ENDPOINT_NAME" ]] && echo "Endpoint Name: $ENDPOINT_NAME"
echo "=================================="

# Check Python dependencies
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
python3 -c "
import sys
required_packages = ['boto3', 'sagemaker', 'sklearn', 'numpy', 'pandas']
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    print(f'❌ Missing packages: {missing_packages}')
    print('Install with: pip install boto3 sagemaker scikit-learn numpy pandas')
    sys.exit(1)
else:
    print('✅ All dependencies satisfied')
"

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Dependency check failed${NC}"
    exit 1
fi

# Check AWS credentials
echo -e "${BLUE}🔐 Checking AWS credentials...${NC}"
aws sts get-caller-identity > /dev/null 2>&1
if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ AWS credentials verified${NC}"
fi

# Build Python command
PYTHON_CMD="python3 run_pipeline.py --mode $MODE"

[[ -n "$ROLE_ARN" ]] && PYTHON_CMD="$PYTHON_CMD --role-arn '$ROLE_ARN'"
[[ -n "$ACCURACY_THRESHOLD" ]] && PYTHON_CMD="$PYTHON_CMD --accuracy-threshold $ACCURACY_THRESHOLD"
[[ -n "$MINIMUM_ACCURACY" ]] && PYTHON_CMD="$PYTHON_CMD --minimum-accuracy $MINIMUM_ACCURACY"
[[ -n "$INSTANCE_TYPE" ]] && PYTHON_CMD="$PYTHON_CMD --instance-type $INSTANCE_TYPE"
[[ -n "$TRAINING_JOB" ]] && PYTHON_CMD="$PYTHON_CMD --training-job '$TRAINING_JOB'"
[[ -n "$ENDPOINT_NAME" ]] && PYTHON_CMD="$PYTHON_CMD --endpoint-name '$ENDPOINT_NAME'"
[[ -n "$OUTPUT_FILE" ]] && PYTHON_CMD="$PYTHON_CMD --output-file '$OUTPUT_FILE'"
[[ "$VERBOSE" == "true" ]] && PYTHON_CMD="$PYTHON_CMD --verbose"

# Execute the pipeline
echo -e "${BLUE}🎯 Starting pipeline execution...${NC}"
echo "Command: $PYTHON_CMD"
echo ""

eval $PYTHON_CMD
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 Pipeline completed successfully!${NC}"
    
    # Show quick access commands if applicable
    if [[ -n "$OUTPUT_FILE" && -f "$OUTPUT_FILE" ]]; then
        echo -e "${BLUE}📄 Results saved to: $OUTPUT_FILE${NC}"
        echo "View results: cat $OUTPUT_FILE | jq"
    fi
    
    # Extract endpoint name if available for testing
    if [[ "$MODE" == "complete" || "$MODE" == "deployment" ]] && [[ -n "$OUTPUT_FILE" ]]; then
        ENDPOINT=$(cat "$OUTPUT_FILE" 2>/dev/null | jq -r '.deployment.deployment_results.endpoint_name // empty' 2>/dev/null || echo "")
        if [[ -n "$ENDPOINT" && "$ENDPOINT" != "null" ]]; then
            echo -e "${BLUE}🧪 Test your endpoint:${NC}"
            echo "python3 scripts/test_endpoint.py --endpoint-name $ENDPOINT"
        fi
    fi
    
else
    echo ""
    echo -e "${RED}❌ Pipeline failed with exit code: $EXIT_CODE${NC}"
    
    if [[ -n "$OUTPUT_FILE" && -f "$OUTPUT_FILE" ]]; then
        echo -e "${YELLOW}📄 Error details saved to: $OUTPUT_FILE${NC}"
        echo "View errors: cat $OUTPUT_FILE | jq"
    fi
    
    echo -e "${YELLOW}💡 Troubleshooting tips:${NC}"
    echo "  • Check AWS permissions and quotas"
    echo "  • Verify SageMaker role has necessary policies"
    echo "  • Check CloudWatch logs for detailed errors"
    echo "  • Run with --verbose for more detailed output"
fi

exit $EXIT_CODE
