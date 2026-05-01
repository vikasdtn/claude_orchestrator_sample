# AWS Bedrock AgentCore Runtime Configuration
# Deploys agents as containerized runtimes on AgentCore

# AgentCore Agent Runtime for Orchestrator
resource "aws_bedrockagentcore_agent_runtime" "orchestrator" {
  agent_runtime_name = "contact-center-orchestrator-${var.environment}"
  description        = "Multi-Agent Orchestrator - Orchestrator"

  runtime_configuration {
    container_configuration {
      container_uri = "${aws_ecr_repository.agents["orchestrator"].repository_url}:latest"
    }
  }

  environment_variables = {
    AWS_REGION                   = var.aws_region
    BEDROCK_MODEL_ID             = var.bedrock_model_id
    AGENTCORE_GATEWAY_URL        = var.agentcore_gateway_url
    SECURITY_AGENT_URL           = var.security_agent_url
    SKIP_SECURITY_VERIFICATION   = tostring(var.skip_security_verification)
    LOG_LEVEL                    = var.environment == "prod" ? "INFO" : "DEBUG"
    PRODUCT_INFO_AGENT_ARN       = aws_bedrockagentcore_agent_runtime.utility_agents["product-info"].arn
    FAQ_AGENT_ARN                = aws_bedrockagentcore_agent_runtime.utility_agents["faq"].arn
    KNOWN_OUTAGES_AGENT_ARN      = aws_bedrockagentcore_agent_runtime.utility_agents["known-outages"].arn
    SERVICE_INFO_AGENT_ARN       = aws_bedrockagentcore_agent_runtime.utility_agents["service-info"].arn
    TICKET_UPDATES_AGENT_ARN     = aws_bedrockagentcore_agent_runtime.utility_agents["ticket-updates"].arn
    BILLING_AGENT_ARN            = aws_bedrockagentcore_agent_runtime.utility_agents["billing"].arn
    SALES_AGENT_ARN              = aws_bedrockagentcore_agent_runtime.utility_agents["sales"].arn
    TECHNICAL_SUPPORT_AGENT_ARN  = aws_bedrockagentcore_agent_runtime.utility_agents["technical-support"].arn
    ACCOUNT_ADMIN_AGENT_ARN      = aws_bedrockagentcore_agent_runtime.utility_agents["account-admin"].arn
  }

  role_arn = aws_iam_role.agentcore_runtime.arn

  tags = {
    Name        = "orchestrator"
    AgentType   = "orchestrator"
    Environment = var.environment
  }
}

# AgentCore Agent Runtimes for Utility Agents
resource "aws_bedrockagentcore_agent_runtime" "utility_agents" {
  for_each = toset(local.utility_agents)

  agent_runtime_name = "contact-center-${each.key}-${var.environment}"
  description        = "Contact Center Utility Agent - ${each.key}"

  runtime_configuration {
    container_configuration {
      container_uri = "${aws_ecr_repository.agents[each.key].repository_url}:latest"
    }
  }

  environment_variables = {
    AWS_REGION            = var.aws_region
    BEDROCK_MODEL_ID      = var.bedrock_model_id
    AGENTCORE_GATEWAY_URL = var.agentcore_gateway_url
    LOG_LEVEL             = var.environment == "prod" ? "INFO" : "DEBUG"
  }

  role_arn = aws_iam_role.agentcore_runtime.arn

  tags = {
    Name        = each.key
    AgentType   = "utility"
    Environment = var.environment
  }
}

# IAM Role for AgentCore Runtime
resource "aws_iam_role" "agentcore_runtime" {
  name = "contact-center-agentcore-runtime-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for AgentCore Runtime - Bedrock Access
resource "aws_iam_role_policy" "agentcore_bedrock" {
  name = "bedrock-access"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:InvokeAgent"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Policy for AgentCore Runtime - ECR Access
resource "aws_iam_role_policy" "agentcore_ecr" {
  name = "ecr-access"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = [for repo in aws_ecr_repository.agents : repo.arn]
      },
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      }
    ]
  })
}

# IAM Policy for AgentCore Runtime - CloudWatch Logs
resource "aws_iam_role_policy" "agentcore_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/bedrock/agentcore/*"
      }
    ]
  })
}

# CloudWatch Log Group for AgentCore
resource "aws_cloudwatch_log_group" "agentcore" {
  name              = "/aws/bedrock/agentcore/contact-center-${var.environment}"
  retention_in_days = var.log_retention_days
}
