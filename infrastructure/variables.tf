variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for agents"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "agentcore_gateway_url" {
  description = "URL of the AgentCore Gateway service"
  type        = string
  default     = ""
}

variable "security_agent_url" {
  description = "URL of the external Security Agent service"
  type        = string
  default     = ""
}

variable "skip_security_verification" {
  description = "Skip security verification (for development only)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
