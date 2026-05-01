"""Sales Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class SalesAgent(BaseUtilityAgent):
    """Agent for handling sales inquiries using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.SALES, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Sales Agent specializing in sales inquiries.

Your responsibilities:
1. Provide information about products and services
2. Share current promotions and discounts
3. Generate quotes for customers
4. Capture sales leads and opportunities

Guidelines:
- Be helpful without being pushy
- Highlight relevant promotions
- For complex quotes, gather requirements first
- Capture lead information when appropriate
- For negotiations or special pricing, escalate to human sales

Use the available tools to access product and promotion information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_promotions",
                "description": "Get current promotions and offers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_type": {
                            "type": "string",
                            "description": "Filter by product type"
                        }
                    }
                }
            },
            {
                "name": "create_quote",
                "description": "Create a sales quote for a customer",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "quantity": {"type": "integer"}
                                }
                            },
                            "description": "Products and quantities"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["customer_id", "products"]
                }
            },
            {
                "name": "capture_lead",
                "description": "Capture a new sales lead",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Lead name"
                        },
                        "email": {
                            "type": "string",
                            "description": "Lead email"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number"
                        },
                        "interest": {
                            "type": "string",
                            "description": "Product/service of interest"
                        }
                    },
                    "required": ["name", "email"]
                }
            },
            {
                "name": "get_product_catalog",
                "description": "Get available products for sale",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Product category filter"
                        }
                    }
                }
            },
            {
                "name": "check_eligibility",
                "description": "Check customer eligibility for upgrades or promotions",
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
        """Execute a sales tool via the AgentCore Gateway."""
        logger.info(f"Executing sales tool: {tool_name}")
        
        if tool_name == "get_promotions":
            query = "SELECT Id, Name, Description__c, Discount__c, ValidUntil__c FROM Promotion__c WHERE Active__c = true"
            if tool_input.get("product_type"):
                query += f" AND ProductType__c = '{tool_input['product_type']}'"
            return self.gateway.query_salesforce(query=query, object_type="Promotion__c")
        
        elif tool_name == "create_quote":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_create_quote",
                    parameters={
                        "customer_id": tool_input["customer_id"],
                        "products": tool_input["products"],
                        "notes": tool_input.get("notes"),
                    },
                )
            )
        
        elif tool_name == "capture_lead":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_create_lead",
                    parameters={
                        "name": tool_input["name"],
                        "email": tool_input["email"],
                        "phone": tool_input.get("phone"),
                        "interest": tool_input.get("interest"),
                    },
                )
            )
        
        elif tool_name == "get_product_catalog":
            query = "SELECT Id, Name, Description, Family, ProductCode FROM Product2 WHERE IsActive = true"
            if tool_input.get("category"):
                query += f" AND Family = '{tool_input['category']}'"
            return self.gateway.query_salesforce(query=query, object_type="Product2")
        
        elif tool_name == "check_eligibility":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="salesforce_check_eligibility",
                    parameters={"customer_id": tool_input["customer_id"]},
                )
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
