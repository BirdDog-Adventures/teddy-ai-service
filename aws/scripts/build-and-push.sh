#!/bin/bash

# Script to build and push Docker image to ECR for Teddy AI Service
# Usage: ./build-and-push.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get environment from argument or default to dev
ENVIRONMENT=${1:-dev}

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

# ECR repository name
ECR_REPOSITORY="${ENVIRONMENT}-teddy-ai"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo -e "${GREEN}Building and pushing Docker image for Teddy AI Service environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}ECR Repository: ${ECR_URI}${NC}"

# Get the script directory and navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../.." &> /dev/null && pwd )"
cd "${PROJECT_ROOT}"

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found in $(pwd)${NC}"
    exit 1
fi

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build --platform linux/amd64 -t ${ECR_REPOSITORY}:latest .

# Tag the image
echo -e "${YELLOW}Tagging image...${NC}"
docker tag ${ECR_REPOSITORY}:latest ${ECR_URI}:latest

# Also tag with timestamp for versioning
TIMESTAMP=$(date +%Y%m%d%H%M%S)
docker tag ${ECR_REPOSITORY}:latest ${ECR_URI}:${TIMESTAMP}

# Push the images
echo -e "${YELLOW}Pushing images to ECR...${NC}"
docker push ${ECR_URI}:latest
docker push ${ECR_URI}:${TIMESTAMP}

echo -e "${GREEN}✅ Docker image built and pushed successfully!${NC}"
echo -e "${GREEN}Image URI: ${ECR_URI}:latest${NC}"
echo -e "${GREEN}Versioned URI: ${ECR_URI}:${TIMESTAMP}${NC}"

# Update the parameter file with the new image URI
PARAM_FILE="aws/cloudformation/parameters/${ENVIRONMENT}.json"
if [ -f "$PARAM_FILE" ]; then
    echo -e "${YELLOW}Updating parameter file with new image URI...${NC}"
    # Update ImageUri parameter
    jq --arg uri "${ECR_URI}:latest" \
       'map(if .ParameterKey == "ImageUri" then .ParameterValue = $uri else . end)' \
       "$PARAM_FILE" > "${PARAM_FILE}.tmp" && mv "${PARAM_FILE}.tmp" "$PARAM_FILE"
    echo -e "${GREEN}Parameter file updated!${NC}"
fi

echo -e "${YELLOW}Next steps:${NC}"
echo -e "${YELLOW}1. Run ./deploy.sh ${ENVIRONMENT} to deploy/update the ECS service${NC}"
echo -e "${YELLOW}2. Or update the ECS service manually to use the new image${NC}"
echo -e "${YELLOW}3. Monitor the deployment in the AWS Console${NC}"
