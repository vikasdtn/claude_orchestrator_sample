"""Service Info Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ServiceInfoAgent(BaseUtilityAgent):
    """Agent for handling service information using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.SERVICE_INFO, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Service Information Agent specializing in service details.

Your responsibilities:
1. Provide service availability and coverage information
2. Explain service plans and subscriptions
3. Detail service features and limitations
4. Help customers understand service options

Guidelines:
- Check availability before making promises
- Be clear about coverage limitations
- Explain plan differences clearly
- For service changes, direct to appropriate channels

Use the available tools to fetch accurate service information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_service_details",
                "description": "Get details about a specific service",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Name of the service"
                        }
                    },
                    "required": ["service_name"]
                }
            },
            {
                "name": "check_service_availability",
                "description": "Check service availability in a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location (address, postcode, region)"
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Type of service to check"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_service_plans",
                "description": "Get available service plans and pricing",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_type": {
                            "type": "string",
                            "description": "Type of service"
                        }
                    }
                }
            },
            {
                "name": "search_service_docs",
                "description": "Search service documentation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a service info tool via the AgentCore Gateway."""
        logger.info(f"Executing service info tool: {tool_name}")
        
        if tool_name == "get_service_details":
            query = f"SELECT Id, Name, Description__c, Status__c, Features__c FROM Service__c WHERE Name LIKE '%{tool_input['service_name']}%'"
            return self.gateway.query_salesforce(query=query, object_type="Service__c")
        
        elif tool_name == "check_service_availability":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="service_availability_check",
                    parameters={
                        "location": tool_input["location"],
                        "service_type": tool_input.get("service_type"),
                    },
                )
            )
        
        elif tool_name == "get_service_plans":
            query = "SELECT Id, Name, Description__c, Price__c, Features__c FROM ServicePlan__c WHERE Active__c = true"
            if tool_input.get("service_type"):
                query += f" AND ServiceType__c = '{tool_input['service_type']}'"
            return self.gateway.query_salesforce(query=query, object_type="ServicePlan__c")
        
        elif tool_name == "search_service_docs":
            return self.gateway.search_confluence(
                query=tool_input["query"],
                space_key="SERVICES",
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
