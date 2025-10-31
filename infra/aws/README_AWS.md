# AWS Deployment Guide

This guide covers deploying the Physics Simulation API to AWS using Terraform and ECS Fargate.

## Architecture Overview

```
Internet → ALB → ECS Fargate Tasks → RDS PostgreSQL
                     ↓
                 ElastiCache Redis
                     ↓
                 S3 (Artifacts)
```

### AWS Services Used

- **ECS Fargate**: Container orchestration for API and worker services
- **Application Load Balancer (ALB)**: Load balancing and SSL termination
- **RDS PostgreSQL**: Managed database for job metadata
- **ElastiCache Redis**: Managed Redis for Celery broker and result backend
- **S3**: Object storage for simulation artifacts
- **VPC**: Network isolation with public/private subnets
- **CloudWatch**: Logging and monitoring
- **IAM**: Security roles and policies

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform** installed (v1.0+)
3. **Docker** for building and pushing images
4. **ECR repository** for your application images

### Required AWS Permissions

Your AWS user/role needs permissions for:
- VPC, Subnet, Security Group management
- ECS, ALB, RDS, ElastiCache operations
- S3 bucket management
- IAM role creation
- CloudWatch logs

## Setup Instructions

### 1. Prepare Container Images

First, build and push your application images to ECR:

```bash
# Create ECR repositories
aws ecr create-repository --repository-name physics-sim-api
aws ecr create-repository --repository-name physics-sim-worker

# Get login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com

# Build and tag images
docker build -t physics-sim-api:latest .
docker build -t physics-sim-worker:latest -f Dockerfile --target worker .

# Tag for ECR
docker tag physics-sim-api:latest YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/physics-sim-api:latest
docker tag physics-sim-worker:latest YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/physics-sim-worker:latest

# Push to ECR
docker push YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/physics-sim-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/physics-sim-worker:latest
```

### 2. Configure Terraform

```bash
cd infra/aws

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
vim terraform.tfvars
```

Required variables to set:
- `aws_region`: Your preferred AWS region
- `db_password`: Secure password for PostgreSQL
- `redis_auth_token`: Secure auth token for Redis
- `app_image`: ECR URI for your application image

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply infrastructure
terraform apply
```

The deployment creates:
- VPC with public/private subnets across 2 AZs
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- S3 bucket for artifacts
- ECS cluster and services
- Application Load Balancer

### 4. Configure DNS (Optional)

If you have a custom domain:

```bash
# Add certificate ARN and domain to terraform.tfvars
certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/..."
domain_name = "api.yourdomain.com"

# Update and apply
terraform apply
```

## Environment-Specific Configurations

### Development
```hcl
environment = "development"
app_count = 1
worker_count = 1
db_instance_class = "db.t3.micro"
redis_node_type = "cache.t3.micro"
```

### Staging
```hcl
environment = "staging"
app_count = 2
worker_count = 2
db_instance_class = "db.t3.small"
redis_node_type = "cache.t3.small"
```

### Production
```hcl
environment = "production"
app_count = 3
worker_count = 4
db_instance_class = "db.t3.medium"
redis_node_type = "cache.t3.medium"
```

## Post-Deployment Configuration

### 1. Run Database Migrations

```bash
# Get ECS task ARN
TASK_ARN=$(aws ecs list-tasks --cluster physics-sim-api-cluster --service-name physics-sim-api-app --query 'taskArns[0]' --output text)

# Run migration
aws ecs execute-command \
    --cluster physics-sim-api-cluster \
    --task $TASK_ARN \
    --container app \
    --interactive \
    --command "alembic upgrade head"
```

### 2. Verify Deployment

```bash
# Get load balancer URL
ALB_URL=$(terraform output -raw load_balancer_url)

# Test health endpoint
curl $ALB_URL/health

# Test API documentation
open $ALB_URL/docs
```

## Switching from Redis to SQS

To use Amazon SQS instead of Redis as the Celery broker:

### 1. Update Application Configuration

Add to your task definition environment variables:
```json
{
  "name": "CELERY_BROKER_URL",
  "value": "sqs://YOUR_ACCESS_KEY:YOUR_SECRET_KEY@"
},
{
  "name": "AWS_SQS_QUEUE_URL",
  "value": "https://sqs.us-west-2.amazonaws.com/123456789012/physics-sim-jobs"
}
```

### 2. Create SQS Queue

```bash
# Create SQS queue
aws sqs create-queue --queue-name physics-sim-jobs --attributes VisibilityTimeout=3600

# Create dead letter queue
aws sqs create-queue --queue-name physics-sim-jobs-dlq

# Configure redrive policy
aws sqs set-queue-attributes \
    --queue-url https://sqs.us-west-2.amazonaws.com/123456789012/physics-sim-jobs \
    --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-west-2:123456789012:physics-sim-jobs-dlq\",\"maxReceiveCount\":3}"}'
```

### 3. Update IAM Permissions

Add SQS permissions to the ECS task role:
```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:SendMessage",
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes"
  ],
  "Resource": [
    "arn:aws:sqs:us-west-2:123456789012:physics-sim-jobs",
    "arn:aws:sqs:us-west-2:123456789012:physics-sim-jobs-dlq"
  ]
}
```

## Monitoring and Logging

### CloudWatch Logs

View application logs:
```bash
aws logs tail /ecs/physics-sim-api --follow
```

### CloudWatch Metrics

Monitor ECS services:
- CPU and memory utilization
- Task count and health
- Load balancer metrics

### CloudWatch Alarms

Set up alarms for:
- High CPU/memory usage
- Task failures
- Database connections
- Redis memory usage

## Scaling Configuration

### Auto Scaling

Enable ECS auto scaling:
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/physics-sim-api-cluster/physics-sim-api-app \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --resource-id service/physics-sim-api-cluster/physics-sim-api-app \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-name cpu-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"}}'
```

## Security Best Practices

### 1. Network Security
- Private subnets for application and database
- Security groups with minimal required access
- NAT gateways for outbound internet access

### 2. Data Encryption
- RDS encryption at rest
- ElastiCache encryption in transit and at rest
- S3 server-side encryption

### 3. Access Control
- IAM roles with least privilege
- No hard-coded credentials
- Use AWS Secrets Manager for sensitive data

### 4. Monitoring
- Enable VPC Flow Logs
- CloudTrail for API calls
- GuardDuty for threat detection

## Cost Optimization

### 1. Right-sizing
- Start with smaller instance types
- Use CloudWatch metrics to optimize
- Consider Graviton2 instances for better price/performance

### 2. Reserved Instances
- Purchase RDS Reserved Instances for production
- Use Savings Plans for ECS Fargate

### 3. Storage Optimization
- Use lifecycle policies for S3 artifacts
- Regular cleanup of old job results
- Monitor and optimize database storage

## Backup and Disaster Recovery

### 1. Database Backups
- Automated RDS backups (7-day retention)
- Manual snapshots before major changes
- Cross-region backup replication for production

### 2. Application Recovery
- Multi-AZ deployment
- Infrastructure as Code for quick rebuild
- S3 cross-region replication for artifacts

## Troubleshooting

### Common Issues

1. **Tasks failing to start**
   ```bash
   # Check service events
   aws ecs describe-services --cluster physics-sim-api-cluster --services physics-sim-api-app
   
   # Check task logs
   aws logs get-log-events --log-group-name /ecs/physics-sim-api --log-stream-name ecs/app/TASK_ID
   ```

2. **Database connection issues**
   ```bash
   # Verify security groups allow connection
   # Check RDS instance status
   aws rds describe-db-instances --db-instance-identifier physics-sim-api-db
   ```

3. **Load balancer health check failures**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
   ```

### Useful Commands

```bash
# View ECS service status
aws ecs describe-services --cluster physics-sim-api-cluster --services physics-sim-api-app

# Scale service
aws ecs update-service --cluster physics-sim-api-cluster --service physics-sim-api-app --desired-count 3

# View recent logs
aws logs tail /ecs/physics-sim-api --since 1h

# Execute command in running task
aws ecs execute-command --cluster physics-sim-api-cluster --task TASK_ARN --container app --interactive --command "/bin/bash"
```

## Cleanup

To destroy all infrastructure:

```bash
terraform destroy
```

**Warning**: This will delete all data including the database and S3 artifacts. Make sure to backup any important data first.

## Support

For issues specific to AWS deployment:
1. Check CloudWatch logs for error details
2. Verify IAM permissions and security groups
3. Ensure ECR images are accessible
4. Review Terraform state for configuration drift