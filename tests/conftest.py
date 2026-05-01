"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, patch

from shared.gateway_client import AgentCoreGatewayClient
from shared.claude_client import ClaudeClient
from shared.models import AgentRequest, Priority, ToolResult


@pytest.fixture
def mock_gateway():
    """Create a mock gateway client."""
    gateway = MagicMock(spec=AgentCoreGatewayClient)
    gateway.gateway_url = "http://mock-gateway:8080"
    gateway.invoke_tool.return_value = ToolResult(
        tool_name="mock_tool", success=True, result={"data": "mock_data"}
    )
    gateway.search_confluence.return_value = ToolResult(
        tool_name="confluence_search", success=True, result={"results": []}
    )
    gateway.query_salesforce.return_value = ToolResult(
        tool_name="salesforce_query", success=True, result={"records": []}
    )
    gateway.query_servicenow.return_value = ToolResult(
        tool_name="servicenow_query", success=True, result={"result": []}
    )
    gateway.get_billing_info.return_value = ToolResult(
        tool_name="billing_get_account", success=True, result={"balance": 0}
    )
    return gateway


@pytest.fixture
def mock_claude():
    """Create a mock Claude client."""
    claude = MagicMock(spec=ClaudeClient)
    claude.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    claude.invoke.return_value = "Mock Claude response"
    claude.invoke_json.return_value = {
        "steps": [
            {
                "step_number": 1,
                "agent_type": "faq",
                "instruction": "Answer the question",
                "depends_on": [],
                "reason": "General question"
            }
        ],
        "estimated_complexity": "low",
        "requires_human_review": False,
    }
    claude.invoke_with_tools.return_value = {
        "text": "Mock response",
        "tool_calls": [],
        "stop_reason": "end_turn",
    }
    return claude


@pytest.fixture
def sample_request():
    """Create a sample agent request."""
    return AgentRequest(
        request_id="test-123",
        query="Test query",
        customer_id="cust-456",
        priority=Priority.MEDIUM,
        context={},
    )


@pytest.fixture
def mock_bedrock_client():
    """Mock the Bedrock runtime client."""
    with patch("boto3.client") as mock:
        yield mock
