"""AgentCore Gateway client for tool invocations."""

import json
import logging
import os
import time
from typing import Any

import boto3
import httpx

from .models import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class AgentCoreGatewayClient:
    """Client for interacting with AgentCore Gateway to invoke tools."""

    def __init__(
        self,
        gateway_url: str | None = None,
        region: str | None = None,
        timeout: int = 30,
    ):
        self.gateway_url = gateway_url or os.environ.get(
            "AGENTCORE_GATEWAY_URL", "http://localhost:8080"
        )
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.timeout = timeout
        self._http_client = httpx.Client(timeout=timeout)
        self._lambda_client = None

    @property
    def lambda_client(self):
        """Lazy initialization of Lambda client."""
        if self._lambda_client is None:
            self._lambda_client = boto3.client("lambda", region_name=self.region)
        return self._lambda_client

    def invoke_tool(self, tool_call: ToolCall) -> ToolResult:
        """Invoke a tool via the AgentCore Gateway."""
        start_time = time.time()
        
        try:
            response = self._http_client.post(
                f"{self.gateway_url}/tools/{tool_call.tool_name}",
                json=tool_call.parameters,
                timeout=tool_call.timeout_seconds,
            )
            response.raise_for_status()
            result_data = response.json()
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result_data,
                execution_time_ms=execution_time,
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Tool invocation failed: {e}")
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=f"HTTP error: {e.response.status_code}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"Tool invocation error: {e}")
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def invoke_tool_lambda(
        self, function_name: str, payload: dict[str, Any]
    ) -> ToolResult:
        """Invoke a tool via Lambda function."""
        start_time = time.time()
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )
            
            result_payload = json.loads(response["Payload"].read())
            execution_time = int((time.time() - start_time) * 1000)
            
            if response.get("FunctionError"):
                return ToolResult(
                    tool_name=function_name,
                    success=False,
                    error=result_payload.get("errorMessage", "Unknown error"),
                    execution_time_ms=execution_time,
                )
            
            return ToolResult(
                tool_name=function_name,
                success=True,
                result=result_payload,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            logger.error(f"Lambda invocation error: {e}")
            return ToolResult(
                tool_name=function_name,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    # Convenience methods for specific tool categories
    
    def query_salesforce(self, query: str, object_type: str) -> ToolResult:
        """Query Salesforce via gateway."""
        return self.invoke_tool(ToolCall(
            tool_name="salesforce_query",
            parameters={"query": query, "object_type": object_type},
        ))

    def search_confluence(self, query: str, space_key: str | None = None) -> ToolResult:
        """Search Confluence knowledge base."""
        params = {"query": query}
        if space_key:
            params["space_key"] = space_key
        return self.invoke_tool(ToolCall(
            tool_name="confluence_search",
            parameters=params,
        ))

    def get_billing_info(self, account_id: str) -> ToolResult:
        """Get billing information for an account."""
        return self.invoke_tool(ToolCall(
            tool_name="billing_get_account",
            parameters={"account_id": account_id},
        ))

    def query_servicenow(
        self, table: str, query: str, limit: int = 10
    ) -> ToolResult:
        """Query ServiceNow."""
        return self.invoke_tool(ToolCall(
            tool_name="servicenow_query",
            parameters={"table": table, "query": query, "limit": limit},
        ))

    def create_servicenow_ticket(
        self, 
        short_description: str,
        description: str,
        category: str,
        priority: int = 3,
    ) -> ToolResult:
        """Create a ServiceNow incident ticket."""
        return self.invoke_tool(ToolCall(
            tool_name="servicenow_create_incident",
            parameters={
                "short_description": short_description,
                "description": description,
                "category": category,
                "priority": priority,
            },
        ))

    def close(self):
        """Close the HTTP client."""
        self._http_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
