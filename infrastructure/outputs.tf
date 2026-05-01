output "ecr_repositories" {
  description = "ECR repository URLs for each agent"
  value = {
    for agent in local.agents : agent => aws_ecr_repository.agents[agent].repository_url
  }
}

output "orchestrator_runtime_arn" {
  description = "Orchestrator AgentCore runtime ARN"
  value       = aws_bedrockagentcore_agent_runtime.orchestrator.arn
}

output "orchestrator_runtime_id" {
  description = "Orchestrator AgentCore runtime ID"
  value       = aws_bedrockagentcore_agent_runtime.orchestrator.id
}

output "utility_agent_runtime_arns" {
  description = "Utility agent AgentCore runtime ARNs"
  value = {
    for agent, runtime in aws_bedrockagentcore_agent_runtime.utility_agents : agent => runtime.arn
  }
}

output "agentcore_role_arn" {
  description = "IAM role ARN for AgentCore runtimes"
  value       = aws_iam_role.agentcore_runtime.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for AgentCore agents"
  value       = aws_cloudwatch_log_group.agentcore.name
}
