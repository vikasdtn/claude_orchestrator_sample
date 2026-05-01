"""Product Information Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ProductInfoAgent(BaseUtilityAgent):
    """Agent for handling product information using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.PRODUCT_INFO, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Product Information Agent specializing in product details.

Your responsibilities:
1. Answer questions about product features and specifications
2. Provide pricing information and comparisons
3. Explain product capabilities and limitations
4. Help customers understand which products suit their needs

Guidelines:
- Search documentation first for detailed specifications
- Use Salesforce for official product and pricing data
- Be accurate - don't guess about specifications
- If information isn't available, acknowledge this clearly
- For complex product comparisons, gather info from multiple sources

Use the available tools to fetch accurate product information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_product_docs",
                "description": "Search product documentation in the knowledge base",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for product information"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Specific product name to filter results"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_product_details",
                "description": "Get detailed product information from the product catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product identifier"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Product name (alternative to ID)"
                        }
                    }
                }
            },
            {
                "name": "get_product_pricing",
                "description": "Get pricing information for a product",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product identifier"
                        }
                    },
                    "required": ["product_id"]
                }
            },
            {
                "name": "compare_products",
                "description": "Compare features and pricing of multiple products",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of product IDs to compare"
                        }
                    },
                    "required": ["product_ids"]
                }
            },
            {
                "name": "get_product_availability",
                "description": "Check product availability and stock status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product identifier"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location to check availability"
                        }
                    },
                    "required": ["product_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a product info tool via the AgentCore Gateway."""
        logger.info(f"Executing product info tool: {tool_name}")
        
        if tool_name == "search_product_docs":
            query = tool_input["query"]
            if tool_input.get("product_name"):
                query = f"{tool_input['product_name']} {query}"
            return self.gateway.search_confluence(query=query, space_key="PRODUCTS")
        
        elif tool_name == "get_product_details":
            if tool_input.get("product_id"):
                query = f"SELECT Id, Name, Description, Family, ProductCode, Features__c FROM Product2 WHERE Id = '{tool_input['product_id']}'"
            else:
                query = f"SELECT Id, Name, Description, Family, ProductCode, Features__c FROM Product2 WHERE Name LIKE '%{tool_input.get('product_name', '')}%'"
            return self.gateway.query_salesforce(query=query, object_type="Product2")
        
        elif tool_name == "get_product_pricing":
            query = f"SELECT UnitPrice, UseStandardPrice, Pricebook2.Name FROM PricebookEntry WHERE Product2Id = '{tool_input['product_id']}'"
            return self.gateway.query_salesforce(query=query, object_type="PricebookEntry")
        
        elif tool_name == "compare_products":
            product_ids = "', '".join(tool_input["product_ids"])
            query = f"SELECT Id, Name, Description, Family, ProductCode FROM Product2 WHERE Id IN ('{product_ids}')"
            return self.gateway.query_salesforce(query=query, object_type="Product2")
        
        elif tool_name == "get_product_availability":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="product_availability_check",
                    parameters={
                        "product_id": tool_input["product_id"],
                        "location": tool_input.get("location"),
                    },
                )
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
