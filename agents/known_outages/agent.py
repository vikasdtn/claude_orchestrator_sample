"""Known Outages Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class KnownOutagesAgent(BaseUtilityAgent):
    """Agent for handling outage queries using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.KNOWN_OUTAGES, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Known Outages Agent specializing in service outage information.

Your responsibilities:
1. Provide current outage status and affected services
2. Share planned maintenance schedules
3. Give estimated resolution times
4. Provide incident updates and history

Guidelines:
- Always check for active incidents first
- Be empathetic when customers are affected by outages
- Provide clear timelines when available
- For critical outages, ensure the customer knows we're working on it

Use the available tools to fetch incident and maintenance information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_active_incidents",
                "description": "Get currently active incidents and outages",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "Filter by severity"
                        },
                        "service": {
                            "type": "string",
                            "description": "Filter by affected service"
                        }
                    }
                }
            },
            {
                "name": "get_planned_maintenance",
                "description": "Get scheduled maintenance windows",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Days to look ahead",
                            "default": 7
                        }
                    }
                }
            },
            {
                "name": "get_incident_details",
                "description": "Get details of a specific incident",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "incident_number": {
                            "type": "string",
                            "description": "Incident number (e.g., INC0012345)"
                        }
                    },
                    "required": ["incident_number"]
                }
            },
            {
                "name": "check_service_impact",
                "description": "Check if a specific service or area is impacted",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Service to check"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location/region to check"
                        }
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute an outage tool via the AgentCore Gateway."""
        logger.info(f"Executing outage tool: {tool_name}")
        
        if tool_name == "get_active_incidents":
            query_parts = ["active=true"]
            if tool_input.get("severity"):
                query_parts.append(f"severity={tool_input['severity']}")
            if tool_input.get("service"):
                query_parts.append(f"cmdb_ci.nameLIKE{tool_input['service']}")
            return self.gateway.query_servicenow(
                table="incident",
                query="^".join(query_parts),
                limit=20,
            )
        
        elif tool_name == "get_planned_maintenance":
            return self.gateway.query_servicenow(
                table="change_request",
                query="type=Maintenance^state=scheduled",
                limit=20,
            )
        
        elif tool_name == "get_incident_details":
            return self.gateway.query_servicenow(
                table="incident",
                query=f"number={tool_input['incident_number']}",
                limit=1,
            )
        
        elif tool_name == "check_service_impact":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="service_impact_check",
                    parameters={
                        "service": tool_input.get("service_name"),
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
