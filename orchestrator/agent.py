"""Multi-Agent Orchestrator - Orchestrator with security verification."""

import json
import logging
import os
import uuid
from typing import Any

import httpx

from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import (
    AgentRequest,
    AgentResponse,
    AgentType,
    ExecutionPlan,
    ExecutionStep,
    OrchestratorPayload,
    OrchestratorResponse,
    Priority,
    RiskLevel,
    SecurityVerificationRequest,
    SecurityVerificationResponse,
)

logger = logging.getLogger(__name__)

# Agent endpoint configuration
AGENT_ENDPOINTS = {
    AgentType.PRODUCT_INFO: os.environ.get("PRODUCT_INFO_AGENT_URL", "http://product-info:8080"),
    AgentType.FAQ: os.environ.get("FAQ_AGENT_URL", "http://faq:8080"),
    AgentType.KNOWN_OUTAGES: os.environ.get("KNOWN_OUTAGES_AGENT_URL", "http://known-outages:8080"),
    AgentType.SERVICE_INFO: os.environ.get("SERVICE_INFO_AGENT_URL", "http://service-info:8080"),
    AgentType.TICKET_UPDATES: os.environ.get("TICKET_UPDATES_AGENT_URL", "http://ticket-updates:8080"),
    AgentType.BILLING: os.environ.get("BILLING_AGENT_URL", "http://billing:8080"),
    AgentType.SALES: os.environ.get("SALES_AGENT_URL", "http://sales:8080"),
    AgentType.TECHNICAL_SUPPORT: os.environ.get("TECHNICAL_SUPPORT_AGENT_URL", "http://technical-support:8080"),
    AgentType.ACCOUNT_ADMIN: os.environ.get("ACCOUNT_ADMIN_AGENT_URL", "http://account-admin:8080"),
}

# External Security Agent configuration
SECURITY_AGENT_URL = os.environ.get("SECURITY_AGENT_URL", "http://security-agent:8080")
SECURITY_VERIFICATION_TIMEOUT = int(os.environ.get("SECURITY_VERIFICATION_TIMEOUT", "30"))
SKIP_SECURITY_VERIFICATION = os.environ.get("SKIP_SECURITY_VERIFICATION", "false").lower() == "true"

PLANNING_SYSTEM_PROMPT = """You are the Multi-Agent Orchestrator orchestrator. Your role is to analyze customer intents and create execution plans that determine which utility agents to invoke.

Available utility agents and their capabilities:
- product_info: Product details, specifications, features, pricing, comparisons
- faq: Frequently asked questions, general knowledge, how-to guides
- known_outages: Current outages, planned maintenance, incident status, service disruptions
- service_info: Service availability, coverage areas, service plans, subscriptions
- ticket_updates: Support ticket status, case updates, ticket history
- billing: Account balance, invoices, payment history, charges, fees
- sales: Promotions, quotes, new services, upgrades, discounts
- technical_support: Troubleshooting, diagnostics, technical issues, error resolution
- account_admin: Account settings, profile updates, contact info, preferences

When creating an execution plan:
1. Analyze the customer intent to identify all relevant domains
2. Determine which agents are needed and in what order
3. Consider dependencies between agents (e.g., need account info before billing details)
4. Estimate complexity (low/medium/high) based on number of agents and query complexity
5. Flag for human review if the query involves sensitive operations or is ambiguous

Respond with a JSON object containing:
{
    "steps": [
        {
            "step_number": 1,
            "agent_type": "agent_name",
            "instruction": "specific instruction for this agent",
            "depends_on": [],
            "reason": "why this agent is needed"
        }
    ],
    "estimated_complexity": "low|medium|high",
    "requires_human_review": false,
    "human_review_reason": null
}"""

SYNTHESIS_SYSTEM_PROMPT = """You are synthesizing responses from multiple utility agents into a coherent, helpful response for the customer. 

Guidelines:
- Combine information logically and avoid repetition
- Use a friendly, professional tone
- If any agent indicated escalation is needed, mention that a specialist will follow up
- Highlight the most important information first
- Keep the response concise but complete"""


class OrchestratorAgent:
    """Multi-Agent Orchestrator with security verification before execution."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
        security_agent_url: str | None = None,
    ):
        self.gateway = gateway_client or AgentCoreGatewayClient()
        self.claude = claude_client or ClaudeClient()
        self.security_agent_url = security_agent_url or SECURITY_AGENT_URL
        self._http_client = httpx.AsyncClient(timeout=60)

    async def process_payload(self, payload: OrchestratorPayload) -> OrchestratorResponse:
        """Process an incoming payload from Lambda with security verification."""
        request_id = str(uuid.uuid4())
        logger.info(f"Processing request {request_id} for customer {payload.customer_id}")

        try:
            # Step 1: Use Claude to create execution plan
            execution_plan = await self._create_execution_plan(payload, request_id)
            logger.info(f"Created execution plan with {len(execution_plan.steps)} steps")

            # Step 2: Send plan to external security agent for verification
            security_response = await self._verify_with_security_agent(
                request_id=request_id,
                payload=payload,
                execution_plan=execution_plan,
            )

            # Step 3: Check if security approved the plan
            if not security_response.approved:
                logger.warning(
                    f"Security agent denied plan execution: {security_response.denial_reason}"
                )
                return OrchestratorResponse(
                    request_id=request_id,
                    customer_id=payload.customer_id,
                    intent=payload.intent,
                    execution_plan=execution_plan,
                    security_verification=security_response,
                    agent_responses=[],
                    final_response=self._build_security_denial_response(security_response),
                    success=False,
                    blocked_by_security=True,
                    requires_escalation=True,
                    escalation_reason=f"Security verification failed: {security_response.denial_reason}",
                )

            # Step 4: Use modified plan if security agent provided one
            plan_to_execute = security_response.modified_plan or execution_plan
            if security_response.modified_plan:
                logger.info("Using modified plan from security agent")

            # Step 5: Execute the approved plan
            agent_responses = await self._execute_plan(
                plan_to_execute, 
                payload,
                security_response.restrictions,
            )

            # Step 6: Synthesize final response
            final_response = await self._synthesize_response(
                payload.intent, agent_responses, plan_to_execute
            )

            # Check if any agent requires escalation
            requires_escalation = any(r.requires_escalation for r in agent_responses)
            escalation_reasons = [
                r.escalation_reason for r in agent_responses if r.requires_escalation
            ]

            return OrchestratorResponse(
                request_id=request_id,
                customer_id=payload.customer_id,
                intent=payload.intent,
                execution_plan=plan_to_execute,
                security_verification=security_response,
                agent_responses=agent_responses,
                final_response=final_response,
                success=True,
                blocked_by_security=False,
                requires_escalation=requires_escalation or plan_to_execute.requires_human_review,
                escalation_reason="; ".join(filter(None, escalation_reasons)) or plan_to_execute.human_review_reason,
            )

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return self._build_error_response(request_id, payload, str(e))


    async def _verify_with_security_agent(
        self,
        request_id: str,
        payload: OrchestratorPayload,
        execution_plan: ExecutionPlan,
    ) -> SecurityVerificationResponse:
        """Send execution plan to external security agent for verification."""
        
        # Allow bypassing security verification for development/testing
        if SKIP_SECURITY_VERIFICATION:
            logger.warning("Security verification skipped (SKIP_SECURITY_VERIFICATION=true)")
            return SecurityVerificationResponse(
                request_id=request_id,
                approved=True,
                risk_level=RiskLevel.LOW,
                audit_id=f"skip-{request_id}",
            )

        verification_request = SecurityVerificationRequest(
            request_id=request_id,
            customer_id=payload.customer_id,
            intent=payload.intent,
            execution_plan=execution_plan,
            priority=payload.priority,
            metadata=payload.metadata,
        )

        try:
            logger.info(f"Sending plan to security agent for verification: {self.security_agent_url}")
            
            response = await self._http_client.post(
                f"{self.security_agent_url}/verify",
                json=verification_request.model_dump(),
                timeout=SECURITY_VERIFICATION_TIMEOUT,
            )
            response.raise_for_status()
            
            security_data = response.json()
            logger.info(
                f"Security verification complete: approved={security_data.get('approved')}, "
                f"risk_level={security_data.get('risk_level')}"
            )
            
            return SecurityVerificationResponse(**security_data)

        except httpx.TimeoutException:
            logger.error("Security agent verification timed out")
            # Fail closed - deny execution if security agent is unavailable
            return SecurityVerificationResponse(
                request_id=request_id,
                approved=False,
                risk_level=RiskLevel.HIGH,
                denial_reason="Security verification timed out - cannot proceed without verification",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Security agent returned error: {e.response.status_code}")
            return SecurityVerificationResponse(
                request_id=request_id,
                approved=False,
                risk_level=RiskLevel.HIGH,
                denial_reason=f"Security agent error: HTTP {e.response.status_code}",
            )

        except Exception as e:
            logger.error(f"Failed to contact security agent: {e}")
            # Fail closed - deny execution if security agent is unavailable
            return SecurityVerificationResponse(
                request_id=request_id,
                approved=False,
                risk_level=RiskLevel.HIGH,
                denial_reason=f"Security verification unavailable: {str(e)}",
            )

    def _build_security_denial_response(self, security_response: SecurityVerificationResponse) -> str:
        """Build a customer-friendly response when security denies the plan."""
        if security_response.risk_level == RiskLevel.CRITICAL:
            return (
                "I apologize, but I'm unable to process this request at this time due to "
                "security protocols. A specialist will review your request and contact you shortly."
            )
        elif security_response.risk_level == RiskLevel.HIGH:
            return (
                "For your security, this request requires additional verification. "
                "A team member will assist you shortly to complete your request safely."
            )
        else:
            return (
                "I'm unable to complete this request automatically. "
                "Please contact our support team for assistance."
            )


    async def _create_execution_plan(
        self, payload: OrchestratorPayload, request_id: str
    ) -> ExecutionPlan:
        """Use Claude to analyze intent and create an execution plan."""
        prompt = f"""Analyze this customer request and create an execution plan.

Customer ID: {payload.customer_id}
Intent: {payload.intent}
Priority: {payload.priority.value}
Additional Context: {json.dumps(payload.metadata)}

Create an execution plan specifying which utility agents to invoke and in what order."""

        try:
            plan_data = self.claude.invoke_json(
                prompt=prompt,
                system_prompt=PLANNING_SYSTEM_PROMPT,
                temperature=0.3,
            )

            steps = [
                ExecutionStep(
                    step_number=step["step_number"],
                    agent_type=AgentType(step["agent_type"]),
                    instruction=step["instruction"],
                    depends_on=step.get("depends_on", []),
                    reason=step["reason"],
                )
                for step in plan_data.get("steps", [])
            ]

            return ExecutionPlan(
                plan_id=f"plan-{request_id}",
                customer_id=payload.customer_id,
                intent=payload.intent,
                steps=steps,
                estimated_complexity=plan_data.get("estimated_complexity", "medium"),
                requires_human_review=plan_data.get("requires_human_review", False),
                human_review_reason=plan_data.get("human_review_reason"),
            )

        except Exception as e:
            logger.error(f"Failed to create execution plan: {e}")
            return self._create_fallback_plan(payload, request_id)

    def _create_fallback_plan(
        self, payload: OrchestratorPayload, request_id: str
    ) -> ExecutionPlan:
        """Create a fallback execution plan using keyword matching."""
        intent_lower = payload.intent.lower()
        steps = []
        step_num = 1

        keyword_mapping = {
            AgentType.BILLING: ["bill", "invoice", "payment", "charge", "balance"],
            AgentType.TECHNICAL_SUPPORT: ["error", "not working", "broken", "issue", "problem"],
            AgentType.KNOWN_OUTAGES: ["outage", "down", "maintenance"],
            AgentType.TICKET_UPDATES: ["ticket", "case", "status"],
            AgentType.PRODUCT_INFO: ["product", "feature", "specification"],
            AgentType.FAQ: ["how", "what", "why", "when"],
            AgentType.SALES: ["buy", "purchase", "upgrade", "promotion"],
            AgentType.ACCOUNT_ADMIN: ["account", "profile", "settings"],
            AgentType.SERVICE_INFO: ["service", "plan", "coverage"],
        }

        for agent_type, keywords in keyword_mapping.items():
            if any(kw in intent_lower for kw in keywords):
                steps.append(ExecutionStep(
                    step_number=step_num,
                    agent_type=agent_type,
                    instruction=payload.intent,
                    depends_on=[],
                    reason=f"Keyword match for {agent_type.value}",
                ))
                step_num += 1

        if not steps:
            steps.append(ExecutionStep(
                step_number=1,
                agent_type=AgentType.FAQ,
                instruction=payload.intent,
                depends_on=[],
                reason="Default fallback to FAQ agent",
            ))

        return ExecutionPlan(
            plan_id=f"plan-{request_id}",
            customer_id=payload.customer_id,
            intent=payload.intent,
            steps=steps,
            estimated_complexity="medium",
            requires_human_review=True,
            human_review_reason="Fallback plan - Claude planning unavailable",
        )


    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        payload: OrchestratorPayload,
        restrictions: list[str] | None = None,
    ) -> list[AgentResponse]:
        """Execute the plan by invoking utility agents in order."""
        responses: list[AgentResponse] = []
        completed_steps: dict[int, AgentResponse] = {}
        restrictions = restrictions or []

        # Log any restrictions from security agent
        if restrictions:
            logger.info(f"Executing with restrictions: {restrictions}")

        pending_steps = list(plan.steps)
        
        while pending_steps:
            ready_steps = [
                step for step in pending_steps
                if all(dep in completed_steps for dep in step.depends_on)
            ]

            if not ready_steps:
                logger.error("Circular dependency detected in execution plan")
                break

            for step in ready_steps:
                context = {
                    f"step_{dep}_response": completed_steps[dep].response
                    for dep in step.depends_on
                    if dep in completed_steps
                }
                
                # Add security restrictions to context
                if restrictions:
                    context["security_restrictions"] = restrictions

                response = await self._invoke_utility_agent(
                    agent_type=step.agent_type,
                    instruction=step.instruction,
                    customer_id=payload.customer_id,
                    priority=payload.priority,
                    context=context,
                )
                
                responses.append(response)
                completed_steps[step.step_number] = response
                pending_steps.remove(step)

        return responses

    async def _invoke_utility_agent(
        self,
        agent_type: AgentType,
        instruction: str,
        customer_id: str,
        priority: Priority,
        context: dict[str, Any],
    ) -> AgentResponse:
        """Invoke a utility agent via HTTP."""
        endpoint = AGENT_ENDPOINTS.get(agent_type)
        request_id = f"orch-{agent_type.value}-{uuid.uuid4().hex[:8]}"

        if not endpoint:
            return AgentResponse(
                request_id=request_id,
                agent_type=agent_type.value,
                success=False,
                response=f"Unknown agent type: {agent_type}",
            )

        try:
            request_data = {
                "request_id": request_id,
                "query": instruction,
                "customer_id": customer_id,
                "priority": priority.value,
                "context": context,
            }

            response = await self._http_client.post(
                f"{endpoint}/process",
                json=request_data,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            
            return AgentResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"Error invoking {agent_type.value} agent: {e}")
            return AgentResponse(
                request_id=request_id,
                agent_type=agent_type.value,
                success=False,
                response=f"Failed to reach {agent_type.value} agent",
                requires_escalation=True,
                escalation_reason=f"Agent communication error: {str(e)}",
            )


    async def _synthesize_response(
        self,
        intent: str,
        agent_responses: list[AgentResponse],
        plan: ExecutionPlan,
    ) -> str:
        """Use Claude to synthesize agent responses into a final customer response."""
        if not agent_responses:
            return "I apologize, but I couldn't process your request. Please try again or speak with a representative."

        responses_summary = "\n\n".join([
            f"Agent: {r.agent_type}\nSuccess: {r.success}\nResponse: {r.response}"
            for r in agent_responses
        ])

        prompt = f"""Customer Intent: {intent}

Execution Plan Complexity: {plan.estimated_complexity}

Agent Responses:
{responses_summary}

Synthesize these responses into a single, coherent response for the customer."""

        try:
            return self.claude.invoke(
                prompt=prompt,
                system_prompt=SYNTHESIS_SYSTEM_PROMPT,
                temperature=0.5,
            )
        except Exception as e:
            logger.error(f"Failed to synthesize response: {e}")
            successful = [r for r in agent_responses if r.success]
            if successful:
                return " ".join(r.response for r in successful)
            return "I encountered an issue processing your request. A specialist will assist you."

    def _build_error_response(
        self, request_id: str, payload: OrchestratorPayload, error: str
    ) -> OrchestratorResponse:
        """Build an error response."""
        return OrchestratorResponse(
            request_id=request_id,
            customer_id=payload.customer_id,
            intent=payload.intent,
            execution_plan=ExecutionPlan(
                plan_id=f"plan-{request_id}",
                customer_id=payload.customer_id,
                intent=payload.intent,
                steps=[],
                estimated_complexity="high",
                requires_human_review=True,
                human_review_reason="Processing error occurred",
            ),
            security_verification=None,
            final_response="I apologize, but I encountered an issue processing your request. A specialist will assist you shortly.",
            success=False,
            requires_escalation=True,
            escalation_reason=f"Processing error: {error}",
        )

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the orchestrator."""
        # Check security agent connectivity
        security_status = "unknown"
        if not SKIP_SECURITY_VERIFICATION:
            try:
                response = await self._http_client.get(
                    f"{self.security_agent_url}/health",
                    timeout=5,
                )
                security_status = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception:
                security_status = "unreachable"

        return {
            "agent_type": "orchestrator",
            "status": "healthy",
            "model_id": self.claude.model_id,
            "security_agent": {
                "url": self.security_agent_url,
                "status": security_status,
                "verification_enabled": not SKIP_SECURITY_VERIFICATION,
            },
            "utility_agents": list(AGENT_ENDPOINTS.keys()),
        }

    async def close(self):
        """Clean up resources."""
        await self._http_client.aclose()
        self.gateway.close()
