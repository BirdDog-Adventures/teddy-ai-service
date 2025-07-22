#!/bin/bash

# Script to create secrets in AWS Secrets Manager for Teddy AI Service
# Usage: ./create-secrets.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get environment from argument or default to dev
ENVIRONMENT=${1:-dev}

echo -e "${GREEN}Creating secrets for Teddy AI Service environment: ${ENVIRONMENT}${NC}"

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    echo -e "${YELLOW}Processing secret: ${secret_name}${NC}"
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" >/dev/null 2>&1; then
        echo -e "${YELLOW}Secret ${secret_name} already exists. Updating...${NC}"
        aws secretsmanager update-secret \
            --secret-id "$secret_name" \
            --secret-string "$secret_value"
    else
        echo -e "${YELLOW}Creating new secret: ${secret_name}${NC}"
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value"
    fi
    
    echo -e "${GREEN}✅ Secret ${secret_name} processed successfully${NC}"
}

# Function to prompt for secret value
prompt_for_secret() {
    local prompt_text=$1
    local default_value=$2
    local secret_value
    
    if [ -n "$default_value" ]; then
        read -p "${prompt_text} [${default_value}]: " secret_value
        secret_value=${secret_value:-$default_value}
    else
        read -s -p "${prompt_text}: " secret_value
        echo
    fi
    
    echo "$secret_value"
}

echo -e "${YELLOW}This script will create/update secrets for the Teddy AI Service.${NC}"
echo -e "${YELLOW}You'll be prompted to enter values for each secret.${NC}"
echo -e "${YELLOW}Press Enter to use default values where provided.${NC}"
echo

# Database Configuration
echo -e "${BLUE}=== Database Configuration ===${NC}"
DB_HOST=$(prompt_for_secret "Database Host" "localhost")
DB_PORT=$(prompt_for_secret "Database Port" "5432")
DB_NAME=$(prompt_for_secret "Database Name" "teddy_ai")
DB_USER=$(prompt_for_secret "Database User" "teddy_user")
DB_PASSWORD=$(prompt_for_secret "Database Password (will be hidden)")
DB_SCHEMA=$(prompt_for_secret "Database Schema" "teddy-ai")

# Redis Configuration
echo -e "${BLUE}=== Redis Configuration ===${NC}"
if [ "$ENVIRONMENT" = "dev" ]; then
    REDIS_URL=$(prompt_for_secret "Redis URL (leave empty to disable for dev/demo)" "")
else
    REDIS_URL=$(prompt_for_secret "Redis URL" "redis://localhost:6379")
fi

# LLM API Keys
echo -e "${BLUE}=== LLM API Keys ===${NC}"
OPENAI_API_KEY=$(prompt_for_secret "OpenAI API Key (will be hidden)")
ANTHROPIC_API_KEY=$(prompt_for_secret "Anthropic API Key (optional, will be hidden)" "")
GOOGLE_API_KEY=$(prompt_for_secret "Google API Key (optional, will be hidden)" "")

# Snowflake Configuration
echo -e "${BLUE}=== Snowflake Configuration ===${NC}"
SNOWFLAKE_ACCOUNT=$(prompt_for_secret "Snowflake Account" "JJODRXK-FP74384")
SNOWFLAKE_USER=$(prompt_for_secret "Snowflake User" "BIRDDOG_GEOVIEWER")
SNOWFLAKE_PASSWORD=$(prompt_for_secret "Snowflake Password (leave empty if using private key auth)" "")
SNOWFLAKE_DATABASE=$(prompt_for_secret "Snowflake Database" "BIRDDOG_DATA")
SNOWFLAKE_SCHEMA=$(prompt_for_secret "Snowflake Schema" "CURATED")
SNOWFLAKE_WAREHOUSE=$(prompt_for_secret "Snowflake Warehouse" "BIRDDOG_WH")
SNOWFLAKE_ROLE=$(prompt_for_secret "Snowflake Role" "DATAENGINEERINGADMIN")
SNOWFLAKE_PRIVATE_KEY_PATH=$(prompt_for_secret "Snowflake Private Key Path" "/app/keys/rsa_key.p8")

# JWT Configuration
echo -e "${BLUE}=== JWT Configuration ===${NC}"
JWT_SECRET_KEY=$(prompt_for_secret "JWT Secret Key (will be hidden)" "$(openssl rand -base64 32 | tr -d '\n')")
JWT_ALGORITHM=$(prompt_for_secret "JWT Algorithm" "HS256")

# Application Configuration
echo -e "${BLUE}=== Application Configuration ===${NC}"
ENABLE_AUTHENTICATION=$(prompt_for_secret "Enable Authentication (true/false)" "false")
DEBUG=$(prompt_for_secret "Debug Mode (true/false)" "false")

echo -e "${YELLOW}Creating secrets in AWS Secrets Manager...${NC}"

# Create the main application secrets
APP_SECRETS=$(cat <<EOF
{
  "DATABASE_URL": "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?options=-csearch_path%3D${DB_SCHEMA}",
  "DATABASE_SCHEMA": "${DB_SCHEMA}",
  "REDIS_URL": "${REDIS_URL}",
  "OPENAI_API_KEY": "${OPENAI_API_KEY}",
  "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
  "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
  "SNOWFLAKE_ACCOUNT": "${SNOWFLAKE_ACCOUNT}",
  "SNOWFLAKE_USER": "${SNOWFLAKE_USER}",
  "SNOWFLAKE_PASSWORD": "${SNOWFLAKE_PASSWORD}",
  "SNOWFLAKE_DATABASE": "${SNOWFLAKE_DATABASE}",
  "SNOWFLAKE_SCHEMA": "${SNOWFLAKE_SCHEMA}",
  "SNOWFLAKE_WAREHOUSE": "${SNOWFLAKE_WAREHOUSE}",
  "SNOWFLAKE_ROLE": "${SNOWFLAKE_ROLE}",
  "SNOWFLAKE_PRIVATE_KEY_PATH": "${SNOWFLAKE_PRIVATE_KEY_PATH}",
  "JWT_SECRET_KEY": "${JWT_SECRET_KEY}",
  "JWT_ALGORITHM": "${JWT_ALGORITHM}",
  "ENABLE_AUTHENTICATION": "${ENABLE_AUTHENTICATION}",
  "DEBUG": "${DEBUG}"
}
EOF
)

create_or_update_secret \
    "${ENVIRONMENT}-teddy-ai-secrets" \
    "$APP_SECRETS" \
    "Teddy AI Service application secrets for ${ENVIRONMENT} environment"

echo -e "${GREEN}🎉 All secrets created successfully!${NC}"
echo -e "${YELLOW}Secret name: ${ENVIRONMENT}-teddy-ai-secrets${NC}"
echo -e "${YELLOW}The ECS task will automatically load these secrets as environment variables.${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${YELLOW}1. Run ./build-and-push.sh ${ENVIRONMENT} to build and push the Docker image${NC}"
echo -e "${YELLOW}2. Run ./deploy.sh ${ENVIRONMENT} to deploy the infrastructure${NC}"
