"""Base class for utility agents with Claude-powered tool selection."""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

from .claude_client import ClaudeClient
from .gateway_client import AgentCoreGatewayClient
from .models import AgentRequest, AgentResponse, AgentType, ToolResult

logger = logging.getLogger(__name__)


class BaseUtilityAgent(ABC):
    """Base class for all utility agents using Claude for intelligent tool selection."""

    def __init__(
        self,
        agent_type: AgentType,
        gateway_client: AgentCoreGatewayClient | None = None,
        claude_client: ClaudeClient | None = None,
    ):
        self.agent_type = agent_type
        self.gateway = gateway_client or AgentCoreGatewayClient()
        self.claude = claude_client or ClaudeClient()

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @property
    @abstractmethod
    def available_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions in Claude tool format."""
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a specific tool and return the result."""
        pass

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process a request using Claude to select and execute tools."""
        logger.info(f"Processing {self.agent_type.value} request: {request.request_id}")
        
        tools_used = []
        tool_results = []
        
        try:
            # Build the prompt with customer context
            prompt = self._build_prompt(request)
            
            # Use Claude to determine which tools to call
            response = self.claude.invoke_with_tools(
                prompt=prompt,
                tools=self.available_tools,
                system_prompt=self.system_prompt,
                temperature=0.3,
            )
            
            # Execute any tool calls Claude requested
            if response["tool_calls"]:
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    
                    logger.info(f"Executing tool: {tool_name}")
                    tools_used.append(tool_name)
                    
                    result = self.execute_tool(tool_name, tool_input)
                    tool_results.append(result)
                
                # Get final response from Claude with tool results
                final_response = await self._get_final_response(
                    request, response["tool_calls"], tool_results
                )
            else:
                # Claude responded without needing tools
                final_response = response["text"]
            
            # Check if escalation is needed
            requires_escalation, escalation_reason = self._check_escalation(
                request, final_response, tool_results
            )
            
            return self._build_response(
                request=request,
                response_text=final_response,
                success=True,
                tools_used=tools_used,
                data={"tool_results": [r.model_dump() for r in tool_results]},
                requires_escalation=requires_escalation,
                escalation_reason=escalation_reason,
            )

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return self._build_response(
                request=request,
                response_text=f"I encountered an issue while processing your request: {str(e)}",
                success=False,
                tools_used=tools_used,
                requires_escalation=True,
                escalation_reason=f"Processing error: {str(e)}",
            )

    def _build_prompt(self, request: AgentRequest) -> str:
        """Build the prompt for Claude including customer context."""
        context_str = ""
        if request.context:
            context_str = f"\n\nAdditional Context:\n{request.context}"
        
        return f"""Customer ID: {request.customer_id or 'Unknown'}
Request Priority: {request.priority.value}

Customer Query: {request.query}{context_str}

Analyze this request and determine which tools to use to best assist the customer."""

    async def _get_final_response(
        self,
        request: AgentRequest,
        tool_calls: list[dict],
        tool_results: list[ToolResult],
    ) -> str:
        """Get final response from Claude after tool execution."""
        # Build tool results summary
        results_summary = []
        for call, result in zip(tool_calls, tool_results):
            results_summary.append(
                f"Tool: {call['name']}\n"
                f"Input: {call['input']}\n"
                f"Success: {result.success}\n"
                f"Result: {result.result if result.success else result.error}"
            )
        
        prompt = f"""Original Query: {request.query}

Tool Execution Results:
{chr(10).join(results_summary)}

Based on these tool results, provide a helpful response to the customer."""

        return self.claude.invoke(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=0.5,
        )

    def _check_escalation(
        self,
        request: AgentRequest,
        response: str,
        tool_results: list[ToolResult],
    ) -> tuple[bool, str | None]:
        """Check if the request should be escalated to a human."""
        # Check for tool failures
        failed_tools = [r for r in tool_results if not r.success]
        if failed_tools:
            return True, f"Tool execution failed: {failed_tools[0].error}"
        
        # Check priority
        if request.priority.value in ["high", "critical"]:
            return True, f"High priority request requires human review"
        
        return False, None

    def _build_response(
        self,
        request: AgentRequest,
        response_text: str,
        success: bool = True,
        tools_used: list[str] | None = None,
        data: dict[str, Any] | None = None,
        confidence: float = 1.0,
        requires_escalation: bool = False,
        escalation_reason: str | None = None,
    ) -> AgentResponse:
        """Build a standardized response."""
        return AgentResponse(
            request_id=request.request_id,
            agent_type=self.agent_type.value,
            success=success,
            response=response_text,
            tools_used=tools_used or [],
            data=data or {},
            confidence=confidence,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
        )

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the agent."""
        return {
            "agent_type": self.agent_type.value,
            "status": "healthy",
            "model_id": self.claude.model_id,
            "gateway_url": self.gateway.gateway_url,
            "available_tools": [t["name"] for t in self.available_tools],
        }
