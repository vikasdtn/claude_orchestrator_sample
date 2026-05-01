"""Account Admin Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentRequest, AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class AccountAdminAgent(BaseUtilityAgent):
    """Agent for handling account administration using Claude for tool selection."""

    SENSITIVE_OPERATIONS = ["close", "cancel", "delete", "transfer", "ownership"]

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.ACCOUNT_ADMIN, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are an Account Admin Agent specializing in account management.

Your responsibilities:
1. Help customers view and update account information
2. Manage contact preferences and settings
3. Handle account verification requests
4. Process account-related administrative tasks

Guidelines:
- Always verify customer identity before making changes
- For sensitive operations (closure, transfer), flag for human approval
- Be clear about what changes are being made
- Confirm changes with the customer

Use the available tools to access and update account information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_account_details",
                "description": "Get account details for a customer",
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
            },
            {
                "name": "update_contact_info",
                "description": "Update customer contact information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "field": {
                            "type": "string",
                            "enum": ["email", "phone", "address"],
                            "description": "Field to update"
                        },
                        "value": {
                            "type": "string",
                            "description": "New value"
                        }
                    },
                    "required": ["customer_id", "field", "value"]
                }
            },
            {
                "name": "get_account_preferences",
                "description": "Get account preferences and settings",
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
            },
            {
                "name": "update_preferences",
                "description": "Update account preferences",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "preferences": {
                            "type": "object",
                            "description": "Preference settings to update"
                        }
                    },
                    "required": ["customer_id", "preferences"]
                }
            },
            {
                "name": "get_account_history",
                "description": "Get account activity history",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Days of history",
                            "default": 30
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute an account admin tool via the AgentCore Gateway."""
        logger.info(f"Executing account admin tool: {tool_name}")
        
        if tool_name == "get_account_details":
            query = f"SELECT Id, Name, Email__c, Phone, BillingAddress, AccountStatus__c FROM Account WHERE Id = '{tool_input['customer_id']}'"
            return self.gateway.query_salesforce(query=query, object_type="Account")
        
        elif tool_name == "update_contact_info":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_update_account",
                    parameters={
                        "account_id": tool_input["customer_id"],
                        "field": tool_input["field"],
                        "value": tool_input["value"],
                    },
                )
            )
        
        elif tool_name == "get_account_preferences":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_get_preferences",
                    parameters={"account_id": tool_input["customer_id"]},
                )
            )
        
        elif tool_name == "update_preferences":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_update_preferences",
                    parameters={
                        "account_id": tool_input["customer_id"],
                        "preferences": tool_input["preferences"],
                    },
                )
            )
        
        elif tool_name == "get_account_history":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_account_history",
                    parameters={
                        "account_id": tool_input["customer_id"],
                        "days": tool_input.get("days", 30),
                    },
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
        """Check if account operation needs human escalation."""
        needs_escalation, reason = super()._check_escalation(request, response, tool_results)
        if needs_escalation:
            return needs_escalation, reason
        
        query_lower = request.query.lower()
        for operation in self.SENSITIVE_OPERATIONS:
            if operation in query_lower:
                return True, f"Sensitive account operation '{operation}' requires human approval"
        
        return False, None
