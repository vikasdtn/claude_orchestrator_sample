terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure your backend
    # bucket = "your-terraform-state-bucket"
    # key    = "contact-center-agents/terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "contact-center-agents"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local variables
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  # All agents (orchestrator + utility)
  agents = [
    "orchestrator",
    "product-info",
    "faq",
    "known-outages",
    "service-info",
    "ticket-updates",
    "billing",
    "sales",
    "technical-support",
    "account-admin"
  ]

  # Utility agents only (excludes orchestrator)
  utility_agents = [
    "product-info",
    "faq",
    "known-outages",
    "service-info",
    "ticket-updates",
    "billing",
    "sales",
    "technical-support",
    "account-admin"
  ]
}
