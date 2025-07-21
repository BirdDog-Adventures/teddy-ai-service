#!/bin/bash

# Script to deploy CloudFormation stacks for Teddy AI Service
# Usage: ./deploy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get environment from argument or default to dev
ENVIRONMENT=${1:-dev}

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

echo -e "${GREEN}Deploying Teddy AI Service infrastructure for environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${YELLOW}AWS Region: ${AWS_REGION}${NC}"

# Function to update parameter file with dynamic values
update_parameters() {
    local param_file=$1
    local vpc_id=$2
    local subnet_ids=$3
    local certificate_arn=$4
    
    # Create a temporary file with updated parameters
    local temp_file="${param_file}.tmp"
    
    # Read the JSON and update VpcId, SubnetIds, and CertificateArn
    jq --arg vpc "$vpc_id" \
       --arg subnets "$subnet_ids" \
       --arg cert "$certificate_arn" \
       'map(
         if .ParameterKey == "VpcId" then .ParameterValue = $vpc
         elif .ParameterKey == "SubnetIds" then .ParameterValue = $subnets
         elif .ParameterKey == "CertificateArn" then .ParameterValue = $cert
         else . end
       )' "$param_file" > "$temp_file"
    
    echo "$temp_file"
}

# Function to deploy a stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local params_file=$3
    
    echo -e "${BLUE}Deploying ${stack_name}...${NC}"
    
    # Build the AWS CLI command
    local cmd="aws cloudformation deploy \
        --template-file ${template_file} \
        --stack-name ${stack_name} \
        --capabilities CAPABILITY_NAMED_IAM"
    
    # Add parameter file if it exists
    if [ -n "$params_file" ] && [ -f "$params_file" ]; then
        cmd="${cmd} --parameter-overrides file://${params_file}"
    fi
    
    # Execute the command
    if eval $cmd; then
        echo -e "${GREEN}✅ ${stack_name} deployed successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to deploy ${stack_name}${NC}"
        exit 1
    fi
}

# Get the script directory and navigate to cloudformation directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CLOUDFORMATION_DIR="$( cd "${SCRIPT_DIR}/../cloudformation" &> /dev/null && pwd )"
cd "${CLOUDFORMATION_DIR}"

# Check if parameter file exists
PARAM_FILE="parameters/${ENVIRONMENT}.json"
if [ ! -f "$PARAM_FILE" ]; then
    echo -e "${RED}Error: Parameter file ${PARAM_FILE} not found!${NC}"
    exit 1
fi

# Get VPC and Subnet information
echo -e "${YELLOW}Getting default VPC information...${NC}"
DEFAULT_VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text)
if [ "$DEFAULT_VPC_ID" == "None" ] || [ -z "$DEFAULT_VPC_ID" ]; then
    echo -e "${RED}Error: No default VPC found!${NC}"
    exit 1
fi
echo -e "${GREEN}Default VPC ID: ${DEFAULT_VPC_ID}${NC}"

# Get default subnets (at least 2 for ALB)
DEFAULT_SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${DEFAULT_VPC_ID}" --query "Subnets[*].SubnetId" --output text | tr '\t' ',')
SUBNET_COUNT=$(echo $DEFAULT_SUBNETS | tr ',' '\n' | wc -l)
if [ $SUBNET_COUNT -lt 2 ]; then
    echo -e "${RED}Error: Need at least 2 subnets for ALB, found ${SUBNET_COUNT}${NC}"
    exit 1
fi
echo -e "${GREEN}Default Subnets: ${DEFAULT_SUBNETS}${NC}"

# Check for ACM certificate
echo -e "${YELLOW}Checking for ACM certificate for domain: ${ENVIRONMENT}.teddy-ai.birddogit.com${NC}"
CERTIFICATE_ARN=$(aws acm list-certificates --query "CertificateSummaryList[?DomainName=='${ENVIRONMENT}.teddy-ai.birddogit.com' || DomainName=='*.teddy-ai.birddogit.com' || DomainName=='*.birddogit.com'].CertificateArn | [0]" --output text)

if [ "$CERTIFICATE_ARN" == "None" ] || [ -z "$CERTIFICATE_ARN" ]; then
    echo -e "${YELLOW}Warning: No ACM certificate found for the domain.${NC}"
    echo -e "${YELLOW}The ALB will only support HTTP. To enable HTTPS, create an ACM certificate and update the stack.${NC}"
    CERTIFICATE_ARN=""
else
    echo -e "${GREEN}Found ACM Certificate: ${CERTIFICATE_ARN}${NC}"
fi

# Deploy stacks in order
echo -e "${GREEN}Starting deployment...${NC}"

# 1. ECR Repository
deploy_stack "${ENVIRONMENT}-teddy-ai-ecr" "ecr-stack.yaml" "$PARAM_FILE"

# 2. IAM Roles
deploy_stack "${ENVIRONMENT}-teddy-ai-iam" "iam-stack.yaml" "$PARAM_FILE"

# 3. Security Groups
UPDATED_PARAMS=$(update_parameters "$PARAM_FILE" "$DEFAULT_VPC_ID" "$DEFAULT_SUBNETS" "$CERTIFICATE_ARN")
deploy_stack "${ENVIRONMENT}-teddy-ai-security" "security-stack.yaml" "$UPDATED_PARAMS"
rm -f "$UPDATED_PARAMS"

# 4. Secrets Manager
if aws secretsmanager describe-secret --secret-id "${ENVIRONMENT}-teddy-ai-secrets" >/dev/null 2>&1; then
    echo -e "${YELLOW}Secrets already exist - skipping secrets stack${NC}"
else
    deploy_stack "${ENVIRONMENT}-teddy-ai-secrets" "secrets-stack.yaml" "$PARAM_FILE"
fi

# 5. ALB
# Update parameters with VPC and subnet info
UPDATED_PARAMS=$(update_parameters "$PARAM_FILE" "$DEFAULT_VPC_ID" "$DEFAULT_SUBNETS" "$CERTIFICATE_ARN")
deploy_stack "${ENVIRONMENT}-teddy-ai-alb" "alb-stack.yaml" "$UPDATED_PARAMS"
rm -f "$UPDATED_PARAMS"

# 6. ECS Cluster and Service
# Check if ImageUri is set in parameters
IMAGE_URI=$(jq -r '.[] | select(.ParameterKey=="ImageUri") | .ParameterValue' "$PARAM_FILE")
if [ -z "$IMAGE_URI" ] || [ "$IMAGE_URI" == "" ]; then
    echo -e "${YELLOW}Warning: ImageUri not set in parameters file.${NC}"
    echo -e "${YELLOW}Please run ./build-and-push.sh first to build and push the Docker image.${NC}"
    echo -e "${YELLOW}Skipping ECS deployment for now.${NC}"
else
    UPDATED_PARAMS=$(update_parameters "$PARAM_FILE" "$DEFAULT_VPC_ID" "$DEFAULT_SUBNETS" "$CERTIFICATE_ARN")
    deploy_stack "${ENVIRONMENT}-teddy-ai-ecs" "ecs-stack.yaml" "$UPDATED_PARAMS"
    rm -f "$UPDATED_PARAMS"
fi

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"

# Get ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks --stack-name "${ENVIRONMENT}-teddy-ai-alb" --query "Stacks[0].Outputs[?OutputKey=='ALBDNSName'].OutputValue" --output text)
echo -e "${GREEN}ALB DNS Name: ${ALB_DNS}${NC}"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "${YELLOW}1. If you haven't already, run ./create-secrets.sh to set up API keys and secrets${NC}"
echo -e "${YELLOW}2. Run ./build-and-push.sh to build and push the Docker image${NC}"
echo -e "${YELLOW}3. Create a Route53 A record for ${ENVIRONMENT}.teddy-ai.birddogit.com pointing to ${ALB_DNS}${NC}"
echo -e "${YELLOW}4. If needed, create an ACM certificate for HTTPS support${NC}"
echo -e "${YELLOW}5. Test the deployment: curl http://${ALB_DNS}/api/v1/health${NC}"
