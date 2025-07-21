# AWS Deployment Guide for Teddy AI Service

This directory contains all the necessary scripts and CloudFormation templates to deploy the Teddy AI Service to AWS using Docker containers on ECS Fargate.

## 🏗️ Architecture Overview

The deployment creates the following AWS resources:

- **ECR Repository**: For storing Docker images
- **ECS Fargate Cluster**: For running containerized applications
- **Application Load Balancer**: For distributing traffic
- **Auto Scaling**: For handling variable load
- **Secrets Manager**: For secure configuration management
- **CloudWatch**: For logging and monitoring
- **IAM Roles**: For secure service permissions

## 📁 Directory Structure

```
aws/
├── scripts/
│   ├── deploy.sh              # Main deployment script
│   ├── build-and-push.sh      # Docker build and ECR push
│   └── create-secrets.sh      # Secrets Manager setup
├── cloudformation/
│   ├── ecr-stack.yaml         # ECR repository
│   ├── iam-stack.yaml         # IAM roles and policies
│   ├── secrets-stack.yaml     # Secrets Manager
│   ├── security-stack.yaml    # Security groups
│   ├── alb-stack.yaml         # Application Load Balancer
│   ├── ecs-stack.yaml         # ECS cluster and service
│   └── parameters/
│       ├── dev.json           # Development environment parameters
│       └── prod.json          # Production environment parameters
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** installed and running
3. **jq** for JSON processing
4. **curl** for testing

### Step 1: Create Secrets

```bash
cd aws/scripts
./create-secrets.sh dev
```

This will prompt you for:
- Database credentials (with teddy_ai schema)
- Redis configuration (disabled by default for dev)
- API keys (OpenAI, Anthropic, Google)
- Snowflake configuration
- JWT settings

### Step 2: Build and Push Docker Image

```bash
./build-and-push.sh dev
```

This will:
- Build the Docker image
- Push to ECR
- Update parameter files with image URI

### Step 3: Deploy Infrastructure

```bash
./deploy.sh dev
```

This will deploy all CloudFormation stacks in the correct order.

## 🔧 Configuration

### Environment Parameters

Edit `cloudformation/parameters/dev.json` or `prod.json`:

```json
[
  {
    "ParameterKey": "TaskCpu",
    "ParameterValue": "1024"
  },
  {
    "ParameterKey": "TaskMemory", 
    "ParameterValue": "2048"
  },
  {
    "ParameterKey": "DesiredCount",
    "ParameterValue": "1"
  }
]
```

### Redis Configuration

- **Development**: Redis is disabled by default (empty REDIS_URL)
- **Production**: Redis can be enabled by providing a valid Redis URL
- **Demo Mode**: Works without Redis for simplified deployment

### Resource Sizing

| Environment | CPU | Memory | Min Tasks | Max Tasks | Redis |
|-------------|-----|--------|-----------|-----------|-------|
| dev         | 1024| 2048   | 1         | 5         | Disabled |
| prod        | 2048| 4096   | 2         | 10        | Enabled |

## 🔐 Security Features

### Secrets Management
- All sensitive data stored in AWS Secrets Manager
- Automatic injection into ECS containers
- No secrets in code or configuration files

### Network Security
- Security groups restrict traffic to necessary ports
- ALB handles SSL termination
- ECS tasks in private subnets with NAT gateway access

### IAM Permissions
- Least privilege access for all roles
- Separate execution and task roles
- CloudWatch logging permissions

## 📊 Monitoring & Logging

### CloudWatch Integration
- Container logs automatically sent to CloudWatch
- Log retention set to 30 days
- Container insights enabled for metrics

### Health Checks
- ALB health checks on `/api/v1/health`
- ECS container health checks
- Auto-recovery on failures

### Auto Scaling
- CPU-based scaling (target: 70%)
- Memory-based scaling (target: 80%)
- Configurable min/max capacity

## 🌐 Domain Setup

### SSL Certificate
1. Request ACM certificate for your domain
2. Update parameter file with certificate ARN
3. Redeploy ALB stack

### Route53 DNS
```bash
# Get ALB DNS name from deployment output
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name dev-teddy-ai-alb \
  --query "Stacks[0].Outputs[?OutputKey=='ALBDNSName'].OutputValue" \
  --output text)

# Create Route53 A record pointing to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "dev.teddy-ai.birddogit.com",
        "Type": "A",
        "AliasTarget": {
          "DNSName": "'$ALB_DNS'",
          "EvaluateTargetHealth": false,
          "HostedZoneId": "ALB_ZONE_ID"
        }
      }
    }]
  }'
```

## 🔄 Deployment Workflows

### Development Deployment
```bash
# Update code and deploy
./build-and-push.sh dev
./deploy.sh dev
```

### Production Deployment
```bash
# Build and test in dev first
./build-and-push.sh dev
./deploy.sh dev

# Test thoroughly, then promote to prod
./build-and-push.sh prod
./deploy.sh prod
```

### Rolling Updates
ECS automatically performs rolling updates when you deploy a new image:
- New tasks start with updated image
- Health checks ensure new tasks are healthy
- Old tasks are terminated after new ones are ready

## 🧪 Testing

### Health Check
```bash
curl http://your-alb-dns/api/v1/health
```

### API Test
```bash
curl -X POST http://your-alb-dns/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, Teddy!",
    "conversation_type": "general"
  }'
```

### Load Test
```bash
# Simple load test
for i in {1..10}; do
  curl -X POST http://your-alb-dns/api/v1/chat/message \
    -H "Content-Type: application/json" \
    -d '{"message": "Test message '$i'", "conversation_type": "general"}' &
done
wait
```

## 🛠️ Troubleshooting

### Common Issues

1. **ECS Tasks Failing to Start**
   ```bash
   # Check ECS service events
   aws ecs describe-services \
     --cluster dev-teddy-ai-cluster \
     --services dev-teddy-ai-service
   
   # Check CloudWatch logs
   aws logs tail /ecs/dev-teddy-ai --follow
   ```

2. **ALB Health Check Failures**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health \
     --target-group-arn $(aws cloudformation describe-stacks \
       --stack-name dev-teddy-ai-alb \
       --query "Stacks[0].Outputs[?OutputKey=='TargetGroupArn'].OutputValue" \
       --output text)
   ```

3. **Secrets Access Issues**
   ```bash
   # Verify secrets exist
   aws secretsmanager describe-secret \
     --secret-id dev-teddy-ai-secrets
   
   # Check IAM permissions
   aws iam simulate-principal-policy \
     --policy-source-arn TASK_ROLE_ARN \
     --action-names secretsmanager:GetSecretValue \
     --resource-arns SECRET_ARN
   ```

### Debugging Commands

```bash
# View all stacks
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name dev-teddy-ai-alb \
  --query "Stacks[0].Outputs"

# Check ECS service status
aws ecs describe-services \
  --cluster dev-teddy-ai-cluster \
  --services dev-teddy-ai-service

# View recent logs
aws logs tail /ecs/dev-teddy-ai --since 1h
```

## 💰 Cost Optimization

### Development Environment
- Use FARGATE_SPOT for cost savings
- Scale down to 0 tasks when not in use
- Use smaller instance sizes

### Production Environment
- Use reserved capacity for predictable workloads
- Implement proper auto-scaling policies
- Monitor and optimize resource usage

### Cost Monitoring
```bash
# Get cost and usage data
aws ce get-cost-and-usage \
  --time-period Start=2023-01-01,End=2023-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## 🔄 Maintenance

### Regular Tasks
- Update Docker base images monthly
- Review and rotate secrets quarterly
- Monitor CloudWatch logs for errors
- Update CloudFormation templates as needed

### Backup Strategy
- ECS task definitions are versioned automatically
- CloudFormation templates in version control
- Secrets backed up in Secrets Manager
- Application data backup depends on external services

## 📞 Support

For deployment issues:
1. Check CloudWatch logs first
2. Review CloudFormation events
3. Verify IAM permissions
4. Test connectivity to external services

## 🎯 Next Steps

After successful deployment:
1. Set up monitoring dashboards
2. Configure alerting rules
3. Implement CI/CD pipeline
4. Set up automated testing
5. Plan disaster recovery procedures
