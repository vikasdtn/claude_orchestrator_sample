"""Ticket Updates Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class TicketUpdatesAgent(BaseUtilityAgent):
    """Agent for handling ticket updates using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.TICKET_UPDATES, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are a Ticket Updates Agent specializing in support ticket information.

Your responsibilities:
1. Provide ticket status and updates
2. Share ticket history and resolution details
3. Help customers track their support requests
4. Add notes to existing tickets when appropriate

Guidelines:
- Verify customer identity before sharing ticket details
- Provide clear status updates with expected timelines
- For urgent tickets, highlight priority status
- Be empathetic about delays or issues

Use the available tools to fetch and update ticket information."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_ticket_status",
                "description": "Get the current status of a support ticket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_number": {
                            "type": "string",
                            "description": "Ticket/case number"
                        }
                    },
                    "required": ["ticket_number"]
                }
            },
            {
                "name": "get_customer_tickets",
                "description": "Get all tickets for a customer",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["open", "closed", "in_progress", "all"],
                            "description": "Filter by status"
                        }
                    },
                    "required": ["customer_id"]
                }
            },
            {
                "name": "get_ticket_history",
                "description": "Get the activity history of a ticket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_number": {
                            "type": "string",
                            "description": "Ticket number"
                        }
                    },
                    "required": ["ticket_number"]
                }
            },
            {
                "name": "add_ticket_note",
                "description": "Add a note or comment to an existing ticket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_number": {
                            "type": "string",
                            "description": "Ticket number"
                        },
                        "note": {
                            "type": "string",
                            "description": "Note content to add"
                        }
                    },
                    "required": ["ticket_number", "note"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a ticket tool via the AgentCore Gateway."""
        logger.info(f"Executing ticket tool: {tool_name}")
        
        if tool_name == "get_ticket_status":
            return self.gateway.query_servicenow(
                table="incident",
                query=f"number={tool_input['ticket_number']}",
                limit=1,
            )
        
        elif tool_name == "get_customer_tickets":
            query = f"caller_id={tool_input['customer_id']}"
            status = tool_input.get("status")
            if status and status != "all":
                query += f"^state={status}"
            return self.gateway.query_servicenow(
                table="incident",
                query=query,
                limit=20,
            )
        
        elif tool_name == "get_ticket_history":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="servicenow_get_history",
                    parameters={"number": tool_input["ticket_number"]},
                )
            )
        
        elif tool_name == "add_ticket_note":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="servicenow_add_comment",
                    parameters={
                        "number": tool_input["ticket_number"],
                        "comment": tool_input["note"],
                    },
                )
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
