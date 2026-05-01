"""FAQ Agent with Claude-powered tool selection."""

import logging
from typing import Any

from shared.base_agent import BaseUtilityAgent
from shared.claude_client import ClaudeClient
from shared.gateway_client import AgentCoreGatewayClient
from shared.models import AgentType, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class FAQAgent(BaseUtilityAgent):
    """Agent for handling FAQs using Claude for tool selection."""

    def __init__(
        self,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        super().__init__(AgentType.FAQ, gateway_client, claude_client)

    @property
    def system_prompt(self) -> str:
        return """You are an FAQ Agent specializing in answering common questions.

Your responsibilities:
1. Answer frequently asked questions accurately
2. Provide clear, concise explanations
3. Direct customers to relevant resources
4. Identify when a question needs specialist assistance

Guidelines:
- Search the knowledge base for accurate answers
- Provide helpful, friendly responses
- If you cannot find an answer, acknowledge this
- For complex or specialized questions, suggest the appropriate agent

Use the available tools to find answers in the knowledge base."""

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_knowledge_base",
                "description": "Search the FAQ knowledge base for answers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category filter (billing, technical, general)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_faq_article",
                "description": "Get a specific FAQ article by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "article_id": {
                            "type": "string",
                            "description": "FAQ article identifier"
                        }
                    },
                    "required": ["article_id"]
                }
            },
            {
                "name": "get_popular_faqs",
                "description": "Get the most popular/frequently viewed FAQs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Category filter"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of FAQs to return",
                            "default": 5
                        }
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute an FAQ tool via the AgentCore Gateway."""
        logger.info(f"Executing FAQ tool: {tool_name}")
        
        if tool_name == "search_knowledge_base":
            query = tool_input["query"]
            if tool_input.get("category"):
                query = f"{tool_input['category']} {query}"
            return self.gateway.search_confluence(query=query, space_key="FAQ")
        
        elif tool_name == "get_faq_article":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="confluence_get_page",
                    parameters={"page_id": tool_input["article_id"]},
                )
            )
        
        elif tool_name == "get_popular_faqs":
            return self.gateway.invoke_tool(
                ToolCall(
                    tool_name="confluence_popular_pages",
                    parameters={
                        "space_key": "FAQ",
                        "category": tool_input.get("category"),
                        "limit": tool_input.get("limit", 5),
                    },
                )
            )
        
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
