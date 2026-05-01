"""Tests for AgentCore Gateway client."""

import pytest
from unittest.mock import MagicMock, patch
import httpx

from shared.gateway_client import AgentCoreGatewayClient
from shared.models import ToolCall, ToolResult


class TestAgentCoreGatewayClient:
    """Tests for AgentCoreGatewayClient."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.dict("os.environ", {}, clear=True):
            client = AgentCoreGatewayClient()
            assert client.gateway_url == "http://localhost:8080"
            assert client.timeout == 30

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        client = AgentCoreGatewayClient(
            gateway_url="http://custom-gateway:9090",
            region="eu-west-1",
            timeout=60,
        )
        assert client.gateway_url == "http://custom-gateway:9090"
        assert client.region == "eu-west-1"
        assert client.timeout == 60

    def test_init_from_environment(self):
        """Test initialization from environment variables."""
        with patch.dict("os.environ", {
            "AGENTCORE_GATEWAY_URL": "http://env-gateway:8080",
            "AWS_REGION": "ap-southeast-1",
        }):
            client = AgentCoreGatewayClient()
            assert client.gateway_url == "http://env-gateway:8080"
            assert client.region == "ap-southeast-1"

    @patch("httpx.Client.post")
    def test_invoke_tool_success(self, mock_post):
        """Test successful tool invocation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "result"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AgentCoreGatewayClient()
        tool_call = ToolCall(
            tool_name="test_tool",
            parameters={"param1": "value1"},
        )
        
        result = client.invoke_tool(tool_call)
        
        assert result.success is True
        assert result.result == {"data": "result"}
        assert result.tool_name == "test_tool"

    @patch("httpx.Client.post")
    def test_invoke_tool_http_error(self, mock_post):
        """Test tool invocation with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )

        client = AgentCoreGatewayClient()
        tool_call = ToolCall(tool_name="failing_tool", parameters={})
        
        result = client.invoke_tool(tool_call)
        
        assert result.success is False
        assert "HTTP error" in result.error

    @patch("httpx.Client.post")
    def test_query_salesforce(self, mock_post):
        """Test Salesforce query convenience method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"records": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AgentCoreGatewayClient()
        result = client.query_salesforce(
            query="SELECT Id FROM Account",
            object_type="Account",
        )
        
        assert result.success is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "salesforce_query" in call_args[0][0]

    @patch("httpx.Client.post")
    def test_search_confluence(self, mock_post):
        """Test Confluence search convenience method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AgentCoreGatewayClient()
        result = client.search_confluence(query="FAQ", space_key="SUPPORT")
        
        assert result.success is True

    @patch("httpx.Client.post")
    def test_query_servicenow(self, mock_post):
        """Test ServiceNow query convenience method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AgentCoreGatewayClient()
        result = client.query_servicenow(
            table="incident",
            query="active=true",
            limit=10,
        )
        
        assert result.success is True

    @patch("httpx.Client.post")
    def test_create_servicenow_ticket(self, mock_post):
        """Test ServiceNow ticket creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"sys_id": "INC001"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AgentCoreGatewayClient()
        result = client.create_servicenow_ticket(
            short_description="Test issue",
            description="Detailed description",
            category="Technical",
            priority=2,
        )
        
        assert result.success is True

    def test_context_manager(self):
        """Test client as context manager."""
        with AgentCoreGatewayClient() as client:
            assert client is not None
        # Should not raise after exit

    @patch("boto3.client")
    def test_lambda_client_lazy_init(self, mock_boto):
        """Test Lambda client lazy initialization."""
        client = AgentCoreGatewayClient()
        assert client._lambda_client is None
        
        _ = client.lambda_client
        mock_boto.assert_called_once_with("lambda", region_name=client.region)
