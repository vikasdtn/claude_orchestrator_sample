#!/bin/bash
# Build and push all agent Docker images to ECR, then deploy to AgentCore

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "=== Multi-Agent Orchestrator System - Build and Deploy ==="
echo "Region: ${AWS_REGION}"
echo "Account: ${AWS_ACCOUNT_ID}"
echo "Environment: ${ENVIRONMENT}"
echo ""

# Authenticate with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# List of agents to build
AGENTS=(
    "orchestrator"
    "product-info:agents/product_info"
    "faq:agents/faq"
    "known-outages:agents/known_outages"
    "service-info:agents/service_info"
    "ticket-updates:agents/ticket_updates"
    "billing:agents/billing"
    "sales:agents/sales"
    "technical-support:agents/technical_support"
    "account-admin:agents/account_admin"
)

# Build and push each agent
echo ""
echo "=== Building and Pushing Docker Images ==="
for agent_entry in "${AGENTS[@]}"; do
    # Parse agent name and path
    if [[ "$agent_entry" == *":"* ]]; then
        agent_name="${agent_entry%%:*}"
        agent_path="${agent_entry##*:}"
    else
        agent_name="$agent_entry"
        agent_path="$agent_entry"
    fi

    echo ""
    echo "Building ${agent_name}..."
    
    IMAGE_NAME="contact-center/${agent_name}"
    IMAGE_URI="${ECR_REGISTRY}/${IMAGE_NAME}:latest"
    
    # Build with buildx for multi-platform support
    docker buildx build \
        --platform linux/amd64 \
        -t ${IMAGE_URI} \
        -f ${agent_path}/Dockerfile \
        --push \
        .
    
    echo "Pushed ${IMAGE_URI}"
done

echo ""
echo "=== All images built and pushed successfully ==="

# Deploy to AgentCore (optional - controlled by DEPLOY flag)
if [[ "${DEPLOY:-false}" == "true" ]]; then
    echo ""
    echo "=== Deploying to AgentCore Runtime ==="
    
    cd infrastructure
    
    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        echo "Initializing Terraform..."
        terraform init
    fi
    
    # Apply Terraform configuration
    echo "Applying Terraform configuration for ${ENVIRONMENT}..."
    terraform apply -var-file=environments/${ENVIRONMENT}.tfvars -auto-approve
    
    echo ""
    echo "=== AgentCore deployment complete ==="
    
    # Output the runtime ARNs
    echo ""
    echo "Agent Runtime ARNs:"
    terraform output -json utility_agent_runtime_arns
    echo ""
    echo "Orchestrator ARN:"
    terraform output orchestrator_runtime_arn
    
    cd ..
fi

echo ""
echo "=== Build complete ==="
echo ""
echo "To deploy to AgentCore, run:"
echo "  DEPLOY=true ENVIRONMENT=${ENVIRONMENT} ./scripts/build_and_push.sh"
echo ""
echo "Or manually apply Terraform:"
echo "  cd infrastructure"
echo "  terraform apply -var-file=environments/${ENVIRONMENT}.tfvars"
