# Jira Stories

## Epic: Multi-Agent Orchestrator Utility Agent System

**Epic Description**: Build an AI-powered multi-agent contact center system using AWS Bedrock AgentCore runtime with Claude for intelligent query routing and tool selection.

---

## Sprint 1: Foundation & Infrastructure

### CCMA-001: Project Setup and Infrastructure Foundation
**Type**: Story  
**Points**: 5  
**Priority**: High

**Description**:  
As a developer, I need the base project structure and AWS infrastructure so that I can begin building agents.

**Acceptance Criteria**:
- [ ] Project directory structure created with shared, orchestrator, agents folders
- [ ] Terraform configuration for AgentCore runtimes
- [ ] ECR repositories created for all agents
- [ ] IAM roles with Bedrock and AgentCore access permissions
- [ ] CI/CD pipeline skeleton (build scripts)

**Technical Notes**:
- Use Terraform 1.5+
- Deploy to AWS Bedrock AgentCore runtime
- Container images stored in ECR

---

### CCMA-002: Shared Components Development
**Type**: Story  
**Points**: 8  
**Priority**: High

**Description**:  
As a developer, I need shared utilities and base classes so that utility agents can be built consistently.

**Acceptance Criteria**:
- [ ] Pydantic models for AgentRequest, AgentResponse, ToolCall, ToolResult
- [ ] ClaudeClient class for Bedrock invocations
- [ ] AgentCoreGatewayClient for external system integration
- [ ] BaseUtilityAgent abstract class with tool selection logic
- [ ] Unit tests for all shared components (>80% coverage)

**Technical Notes**:
- Use Claude 3 Sonnet model
- Gateway client should support Salesforce, Confluence, ServiceNow, Billing
- Base agent should handle Claude tool calling flow

---

### CCMA-003: Orchestrator Agent - Core Implementation
**Type**: Story  
**Points**: 13  
**Priority**: High

**Description**:  
As a system, I need an orchestrator agent that receives customer intents and creates execution plans using Claude.

**Acceptance Criteria**:
- [ ] OrchestratorPayload model (customer_id, intent)
- [ ] ExecutionPlan and ExecutionStep models
- [ ] Claude-based execution plan generation
- [ ] Fallback keyword-based planning when Claude unavailable
- [ ] Plan execution with dependency handling
- [ ] Response synthesis using Claude
- [ ] FastAPI server with /process and /health endpoints
- [ ] Unit tests for orchestrator logic

**Technical Notes**:
- Execution plan should support step dependencies
- Parallel execution of independent steps (future enhancement)
- Escalation flag based on complexity

---

## Sprint 2: Utility Agents - Part 1

### CCMA-004: Billing Agent Implementation
**Type**: Story  
**Points**: 5  
**Priority**: High

**Description**:  
As a customer, I want to inquire about my billing information so that I can understand my charges.

**Acceptance Criteria**:
- [ ] BillingAgent class extending BaseUtilityAgent
- [ ] Tools: get_account_balance, get_invoices, get_payment_history, get_charge_details
- [ ] Escalation for disputes, refunds, payment plans
- [ ] Integration with billing system via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-005: FAQ Agent Implementation
**Type**: Story  
**Points**: 3  
**Priority**: High

**Description**:  
As a customer, I want to get answers to common questions so that I can self-serve.

**Acceptance Criteria**:
- [ ] FAQAgent class extending BaseUtilityAgent
- [ ] Tools: search_knowledge_base, get_faq_article, get_popular_faqs
- [ ] Integration with Confluence via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-006: Technical Support Agent Implementation
**Type**: Story  
**Points**: 8  
**Priority**: High

**Description**:  
As a customer, I want technical troubleshooting assistance so that I can resolve issues.

**Acceptance Criteria**:
- [ ] TechnicalSupportAgent class extending BaseUtilityAgent
- [ ] Tools: search_troubleshooting_guides, check_known_issues, run_diagnostic, create_support_ticket
- [ ] Escalation for urgent/critical issues
- [ ] Integration with Confluence and ServiceNow via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-007: Known Outages Agent Implementation
**Type**: Story  
**Points**: 3  
**Priority**: Medium

**Description**:  
As a customer, I want to check for service outages so that I know if issues are on my end.

**Acceptance Criteria**:
- [ ] KnownOutagesAgent class extending BaseUtilityAgent
- [ ] Tools: get_active_incidents, get_planned_maintenance, get_incident_details
- [ ] Integration with ServiceNow via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

## Sprint 3: Utility Agents - Part 2

### CCMA-008: Product Info Agent Implementation
**Type**: Story  
**Points**: 5  
**Priority**: Medium

**Description**:  
As a customer, I want product information so that I can make informed decisions.

**Acceptance Criteria**:
- [ ] ProductInfoAgent class extending BaseUtilityAgent
- [ ] Tools: search_product_docs, get_product_details, get_product_pricing, compare_products
- [ ] Integration with Confluence and Salesforce via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-009: Sales Agent Implementation
**Type**: Story  
**Points**: 5  
**Priority**: Medium

**Description**:  
As a customer, I want to inquire about purchases and promotions so that I can buy services.

**Acceptance Criteria**:
- [ ] SalesAgent class extending BaseUtilityAgent
- [ ] Tools: get_promotions, create_quote, capture_lead, get_product_catalog
- [ ] Integration with Salesforce via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-010: Account Admin Agent Implementation
**Type**: Story  
**Points**: 5  
**Priority**: Medium

**Description**:  
As a customer, I want to manage my account settings so that my information is up to date.

**Acceptance Criteria**:
- [ ] AccountAdminAgent class extending BaseUtilityAgent
- [ ] Tools: get_account_details, update_contact_info, get/update_preferences
- [ ] Escalation for sensitive operations (close, transfer)
- [ ] Integration with Salesforce via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-011: Service Info Agent Implementation
**Type**: Story  
**Points**: 3  
**Priority**: Medium

**Description**:  
As a customer, I want service availability information so that I know what's available.

**Acceptance Criteria**:
- [ ] ServiceInfoAgent class extending BaseUtilityAgent
- [ ] Tools: get_service_details, check_service_availability, get_service_plans
- [ ] Integration with Salesforce and Confluence via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

### CCMA-012: Ticket Updates Agent Implementation
**Type**: Story  
**Points**: 3  
**Priority**: Medium

**Description**:  
As a customer, I want to check my support ticket status so that I know progress.

**Acceptance Criteria**:
- [ ] TicketUpdatesAgent class extending BaseUtilityAgent
- [ ] Tools: get_ticket_status, get_customer_tickets, get_ticket_history, add_ticket_note
- [ ] Integration with ServiceNow via Gateway
- [ ] FastAPI server and Dockerfile
- [ ] Unit tests

---

## Sprint 4: Integration & Testing

### CCMA-013: End-to-End Integration Testing
**Type**: Story  
**Points**: 8  
**Priority**: High

**Description**:  
As a QA engineer, I need integration tests to verify the complete flow works correctly.

**Acceptance Criteria**:
- [ ] Integration test suite for orchestrator → utility agent flow
- [ ] Mock Gateway responses for testing
- [ ] Test scenarios for each agent type
- [ ] Test multi-agent execution plans
- [ ] Test escalation scenarios
- [ ] Test error handling and fallbacks

---

### CCMA-014: Docker Compose Local Environment
**Type**: Story  
**Points**: 3  
**Priority**: Medium

**Description**:  
As a developer, I need a local development environment so that I can test without AWS.

**Acceptance Criteria**:
- [ ] docker-compose.yml with all services
- [ ] Environment variable configuration
- [ ] Local mock gateway (optional)
- [ ] Documentation for local setup

---

### CCMA-015: AgentCore Deployment Pipeline
**Type**: Story  
**Points**: 5  
**Priority**: High

**Description**:  
As a DevOps engineer, I need automated deployment to AgentCore so that releases are consistent.

**Acceptance Criteria**:
- [ ] Build script for all Docker images
- [ ] Push to ECR automation
- [ ] Terraform apply automation for AgentCore runtimes
- [ ] Environment-specific configurations (dev, staging, prod)
- [ ] Rollback procedures documented

---

## Sprint 5: Observability & Production Readiness

### CCMA-016: Monitoring and Alerting Setup
**Type**: Story  
**Points**: 5  
**Priority**: High

**Description**:  
As an operations engineer, I need monitoring so that I can track system health.

**Acceptance Criteria**:
- [ ] CloudWatch dashboards for AgentCore runtimes
- [ ] Key metrics: latency, error rate, throughput
- [ ] Alerts for high error rates (>5%)
- [ ] Alerts for latency spikes (p95 > 10s)
- [ ] Bedrock usage tracking

---

### CCMA-017: Documentation
**Type**: Story  
**Points**: 3  
**Priority**: Medium

**Description**:  
As a developer, I need documentation so that I can understand and maintain the system.

**Acceptance Criteria**:
- [ ] Installation guide
- [ ] Developer guide
- [ ] Architecture design document
- [ ] API reference
- [ ] Operations guide

---

### CCMA-018: Security Hardening
**Type**: Story  
**Points**: 5  
**Priority**: High

**Description**:  
As a security engineer, I need security controls so that the system is production-ready.

**Acceptance Criteria**:
- [ ] IAM role least-privilege review
- [ ] No hardcoded credentials
- [ ] Secrets management (AWS Secrets Manager)
- [ ] Audit logging enabled
- [ ] Security verification integration

---

## Backlog

### CCMA-019: Parallel Agent Execution
**Type**: Enhancement  
**Points**: 8  
**Priority**: Low

**Description**:  
Optimize execution plan to run independent steps in parallel.

---

### CCMA-020: Conversation Memory
**Type**: Enhancement  
**Points**: 13  
**Priority**: Low

**Description**:  
Add session-based conversation memory using AgentCore Memory Service.

---

### CCMA-021: A/B Testing Framework
**Type**: Enhancement  
**Points**: 8  
**Priority**: Low

**Description**:  
Enable A/B testing of different Claude prompts and models.

---

## Story Point Reference

| Points | Effort |
|--------|--------|
| 1-2 | Few hours |
| 3 | 1 day |
| 5 | 2-3 days |
| 8 | 1 week |
| 13 | 2 weeks |
