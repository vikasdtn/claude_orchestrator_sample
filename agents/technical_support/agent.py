"""Technical Support Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentRequest, AgentResponse, AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class TechnicalSupportAgent(BaseUtilityAgent):
    """Agent for handling technical support using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.TECHNICAL_SUPPORT, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Technical Support Agent specializing in troubleshooting.

Your responsibilities:
1. Diagnose technical issues reported by customers
2. Provide step-by-step troubleshooting guidance
3. Search knowledge base for known solutions
4. Run diagnostics when appropriate
5. Create support tickets for unresolved issues

Guidelines:
- Start with the simplest solutions first
- Search the knowledge base before suggesting complex fixes
- Check for known issues that might explain the problem
- If the issue cannot be resolved, create a support ticket
- For critical or urgent issues, always flag for human escalation

Use the available tools to diagnose issues and find solutions."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_troubleshooting_guides",
                "description": "Search the knowledge base for troubleshooting guides and solutions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue": {
                            "type": "string",
                            "description": "Description of the technical issue"
                        },
                        "product": {
                            "type": "string",
                            "description": "Product or service name (optional)"
                        }
                    },
                    "required": ["issue"]
                }
            },
            {
                "name": "check_known_issues",
                "description": "Check for known issues or bugs affecting a product",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product": {
                            "type": "string",
                            "description": "Product name"
                        },
                        "version": {
                            "type": "string",
                            "description": "Product version (optional)"
                        }
                    },
                    "required": ["product"]
                }
            },
            {
                "name": "run_diagnostic",
                "description": "Run a remote diagnostic check on customer's service",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "diagnostic_type": {
                            "type": "string",
                            "enum": ["connectivity", "performance", "configuration", "full"],
                            "description": "Type of diagnostic to run"
                        }
                    },
                    "required": ["customer_id", "diagnostic_type"]
                }
            },
            {
                "name": "create_support_ticket",
                "description": "Create a support ticket for issues that cannot be resolved immediately",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "issue_summary": {
                            "type": "string",
                            "description": "Brief summary of the issue"
                        },
                        "issue_details": {
                            "type": "string",
                            "description": "Detailed description of the issue"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority level 1-5 (1 highest)",
                            "default": 3
                        }
                    },
                    "required": ["customer_id", "issue_summary", "issue_details"]
                }
            },
            {
                "name": "get_service_status",
                "description": "Get the current status of a customer's service",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a technical support tool via the AgentCore Gateway."""
        logger.info(f"Executing tech support tool: {tool_name}")
        
        if tool_name == "search_troubleshooting_guides":
            query = f"troubleshooting {tool_input.get('product', '')} {tool_input['issue']}".strip()
            return self.gateway.search_confluence(query=query, space_key="TECHSUPPORT")
        
        elif tool_name == "check_known_issues":
            query = f"cmdb_ci.nameLIKE{tool_input['product']}"
            if tool_input.get("version"):
                query += f"^version={tool_input['version']}"
            return self.gateway.query_servicenow(table="problem", query=query, limit=10)
        
        elif tool_name == "run_diagnostic":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="diagnostic_run",
                    parameters={
                        "customer_id": tool_input["customer_id"],
                        "type": tool_input["diagnostic_type"],
                    },
                )
            )
        
        elif tool_name == "create_support_ticket":
            return self.gateway.create_servicenow_ticket(
                short_description=tool_input["issue_summary"],
                description=f"Customer: {tool_input['customer_id']}\n\n{tool_input['issue_details']}",
                category="Technical Support",
                priority=tool_input.get("priority", 3),
            )
        
        elif tool_name == "get_service_status":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="service_status_check",
                    parameters={"customer_id": tool_input["customer_id"]},
                )
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

    def _check_escalation(
        self,
        request: AgentRequest,
        response: str,
        tool_results: list[ToolResult],
    ) -> tuple[bool, str | None]:
        """Check if technical support request needs escalation."""
        needs_escalation, reason = super()._check_escalation(request, response, tool_results)
        if needs_escalation:
            return needs_escalation, reason
        
        # Check for urgent keywords
        urgent_keywords = ["urgent", "critical", "emergency", "down", "not working", "outage"]
        query_lower = request.query.lower()
        
        for keyword in urgent_keywords:
            if keyword in query_lower:
                return True, f"Urgent technical issue: '{keyword}' detected"
        
        return False, None
