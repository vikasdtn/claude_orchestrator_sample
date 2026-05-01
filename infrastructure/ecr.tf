# ECR Repositories for each agent
resource "aws_ecr_repository" "agents" {
  for_each = toset(local.agents)

  name                 = "contact-center/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Agent = each.key
  }
}

# Lifecycle policy for ECR repositories
resource "aws_ecr_lifecycle_policy" "agents" {
  for_each   = aws_ecr_repository.agents
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
