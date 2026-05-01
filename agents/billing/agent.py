"""Billing Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentRequest, AgentResponse, AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class BillingAgent(BaseUtilityAgent):
    """Agent for handling billing inquiries using Claude for tool selection."""

    # Keywords that require human escalation
    ESCALATION_KEYWORDS = ["dispute", "refund", "payment plan", "arrangement", "cancel", "fraud"]

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.BILLING, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Billing Agent specializing in billing and payment inquiries.

Your responsibilities:
1. Provide billing and invoice information
2. Explain charges and fees clearly
3. Share payment status and history
4. Help customers understand their bills

Guidelines:
- Always verify you have the customer_id before accessing billing data
- Be clear and specific about amounts and dates
- For disputes, refunds, or payment arrangements, indicate that human assistance is needed
- Never make promises about refunds or credits without human approval

Use the available tools to fetch billing information from the billing system."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_account_balance",
                "description": "Get the current account balance and payment status for a customer",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Customer account ID"
                        }
                    },
                    "required": ["account_id"]
                }
            },
            {
                "name": "get_invoices",
                "description": "Get recent invoices for a customer account",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Customer account ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of invoices to retrieve (default 5)",
                            "default": 5
                        }
                    },
                    "required": ["account_id"]
                }
            },
            {
                "name": "get_payment_history",
                "description": "Get payment history for a customer account",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Customer account ID"
                        },
                        "months": {
                            "type": "integer",
                            "description": "Number of months of history (default 6)",
                            "default": 6
                        }
                    },
                    "required": ["account_id"]
                }
            },
            {
                "name": "get_charge_details",
                "description": "Get detailed explanation of a specific charge on an invoice",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Customer account ID"
                        },
                        "charge_id": {
                            "type": "string",
                            "description": "The charge identifier to explain"
                        }
                    },
                    "required": ["account_id", "charge_id"]
                }
            },
            {
                "name": "get_upcoming_charges",
                "description": "Get upcoming or pending charges for a customer",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Customer account ID"
                        }
                    },
                    "required": ["account_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a billing tool via the AgentCore Gateway."""
        logger.info(f"Executing billing tool: {tool_name} with input: {tool_input}")
        
        if tool_name == "get_account_balance":
            return self.gateway.get_billing_info(tool_input["account_id"])
        
        elif tool_name == "get_invoices":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="billing_get_invoices",
                    parameters={
                        "account_id": tool_input["account_id"],
                        "limit": tool_input.get("limit", 5),
                    },
                )
            )
        
        elif tool_name == "get_payment_history":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="billing_payment_history",
                    parameters={
                        "account_id": tool_input["account_id"],
                        "months": tool_input.get("months", 6),
                    },
                )
            )
        
        elif tool_name == "get_charge_details":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="billing_charge_details",
                    parameters={
                        "account_id": tool_input["account_id"],
                        "charge_id": tool_input["charge_id"],
                    },
                )
            )
        
        elif tool_name == "get_upcoming_charges":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="billing_upcoming_charges",
                    parameters={"account_id": tool_input["account_id"]},
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
        """Check if billing request needs human escalation."""
        # First check parent class conditions
        needs_escalation, reason = super()._check_escalation(request, response, tool_results)
        if needs_escalation:
            return needs_escalation, reason
        
        # Check for billing-specific escalation keywords
        query_lower = request.query.lower()
        for keyword in self.ESCALATION_KEYWORDS:
            if keyword in query_lower:
                return True, f"Billing action '{keyword}' requires human approval"
        
        return False, None
