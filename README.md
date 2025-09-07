# 🚀 SageMaker Unified Studio MLOps Platform

A **complete MLOps platform** that combines AWS SageMaker Unified Studio with Infrastructure as Code (Terraform) and automated ML pipelines for enterprise machine learning workflows.

## ✨ What You Get

- 🏗️ **Complete AWS Infrastructure**: SageMaker Unified Studio + supporting services
- 🤖 **Data Science Workspace**: JupyterLab, Canvas (no-code ML), RStudio, Bedrock AI
- 🔄 **Automated ML Pipeline**: Training, deployment, testing, and notifications
- 🔒 **Enterprise Security**: CIS-compliant with proper IAM and networking
- 📊 **Sample Project**: Iris classification with end-to-end workflow

## 🚀 Quick Start

### 1. Prerequisites
```bash
aws --version        # AWS CLI v2
terraform --version  # Terraform >= 1.0
python3 --version   # Python 3.8+
aws configure       # Set up credentials
```

### 2. Deploy Infrastructure
```bash
git clone <repository-url>
cd sagemaker-unified-studio-terraform/terraform

# Configure your settings
cp terraform.tfvars.example terraform.tfvars
# Edit: project_name, aws_region, domain_users

# Deploy
terraform init
terraform apply
```

### 3. Access Your Platform
```bash
# Get studio URL
STUDIO_URL=$(terraform output -raw sagemaker_domain_info | jq -r '.domain_url')
echo "🎯 Access: $STUDIO_URL"
```

### 4. Run Sample ML Pipeline
```bash
cd ../
pip install -r requirements.txt

# Get role from Terraform output
ROLE_ARN=$(cd terraform && terraform output -raw sagemaker_user_profile_role_arn)

# Run iris classification pipeline
./run_mlops_pipeline.sh --role-arn $ROLE_ARN
```

## 📁 Project Structure

```
├── 🏗️ terraform/              # Infrastructure as Code
│   ├── main.tf                # Core configuration
│   ├── sagemaker.tf           # SageMaker Unified Studio
│   ├── iam.tf                 # Security & roles
│   ├── s3.tf                  # Storage
│   └── networking.tf          # VPC & security
│
├── 🤖 pipeline/               # ML Pipeline (see pipeline/PIPELINE_README.md)
│   ├── training.py            # Model training
│   ├── deployment.py          # Deployment logic
│   ├── testing.py             # Testing & validation
│   └── notifications.py       # Alerts & notifications
│
├── 📊 scripts/                # Utilities
├── 📚 notebook/               # Sample notebooks
├── 📈 data/                   # Sample data (iris.csv)
│
├── run_pipeline.py            # Pipeline orchestrator
├── run_mlops_pipeline.sh      # User-friendly wrapper
└── requirements.txt           # Python dependencies
```

## 🏗️ What Gets Deployed

### AWS Infrastructure
- **SageMaker Unified Studio**: Complete data science workspace
- **S3 Buckets**: Model artifacts and data storage (encrypted)
- **IAM Roles**: Least-privilege access for all services
- **VPC & Security**: Isolated networking with security groups
- **CloudWatch**: Logging and monitoring

### Data Science Workspace Features
- **JupyterLab**: Interactive development
- **Canvas**: No-code ML for business users  
- **RStudio**: R-based statistical analysis
- **Bedrock**: Generative AI integration
- **Data Catalog**: Data discovery and governance

## 📚 Documentation

- 📖 **[Pipeline Documentation](pipeline/PIPELINE_README.md)**: ML pipeline technical details
- 📓 **[Workflow Guide](notebook/data_scientist_workflow_guide.ipynb)**: Step-by-step tutorial
- 🏗️ **Terraform Files**: Each .tf file has inline documentation

## 🧹 Cleanup

```bash
cd terraform
terraform destroy -auto-approve
```

## 🔧 Troubleshooting

**Permission Issues**
```bash
aws sts get-caller-identity  # Verify AWS access
```

**Resource Limits**
```bash
aws service-quotas get-service-quota --service-code sagemaker --quota-code L-1194F171
```

**Pipeline Issues**  
See [Pipeline README](pipeline/PIPELINE_README.md) for detailed troubleshooting.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Submit pull request with clear description

## 📄 License

MIT License - see LICENSE file for details.

---

*🚀 Enterprise MLOps made simple*
