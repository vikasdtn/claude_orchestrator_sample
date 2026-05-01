"""Tests for Claude client."""

import json
import pytest
from unittest.mock import MagicMock, patch

from shared.claude_client import ClaudeClient


class TestClaudeClient:
    """Tests for ClaudeClient."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.dict("os.environ", {}, clear=True):
            client = ClaudeClient()
            assert "claude" in client.model_id.lower()
            assert client.max_tokens == 4096

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        client = ClaudeClient(
            model_id="anthropic.claude-3-opus-20240229-v1:0",
            region="eu-west-1",
            max_tokens=8192,
        )
        assert client.model_id == "anthropic.claude-3-opus-20240229-v1:0"
        assert client.region == "eu-west-1"
        assert client.max_tokens == 8192

    @patch("boto3.client")
    def test_invoke_calls_bedrock(self, mock_boto):
        """Test that invoke calls Bedrock runtime."""
        mock_bedrock = MagicMock()
        mock_boto.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps({
                    "content": [{"type": "text", "text": "Hello"}]
                }).encode()
            )
        }

        client = ClaudeClient()
        result = client.invoke("Test prompt")

        assert result == "Hello"
        mock_bedrock.invoke_model.assert_called_once()

    @patch("boto3.client")
    def test_invoke_with_system_prompt(self, mock_boto):
        """Test invoke includes system prompt."""
        mock_bedrock = MagicMock()
        mock_boto.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps({
                    "content": [{"type": "text", "text": "Response"}]
                }).encode()
            )
        }

        client = ClaudeClient()
        client.invoke("Test", system_prompt="You are helpful")

        call_args = mock_bedrock.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        assert body["system"] == "You are helpful"


    @patch("boto3.client")
    def test_invoke_json_parses_response(self, mock_boto):
        """Test invoke_json parses JSON from response."""
        mock_bedrock = MagicMock()
        mock_boto.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps({
                    "content": [{"type": "text", "text": '{"key": "value"}'}]
                }).encode()
            )
        }

        client = ClaudeClient()
        result = client.invoke_json("Return JSON")

        assert result == {"key": "value"}

    @patch("boto3.client")
    def test_invoke_json_handles_markdown_blocks(self, mock_boto):
        """Test invoke_json strips markdown code blocks."""
        mock_bedrock = MagicMock()
        mock_boto.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps({
                    "content": [{"type": "text", "text": '```json\n{"key": "value"}\n```'}]
                }).encode()
            )
        }

        client = ClaudeClient()
        result = client.invoke_json("Return JSON")

        assert result == {"key": "value"}

    @patch("boto3.client")
    def test_invoke_with_tools(self, mock_boto):
        """Test invoke_with_tools handles tool responses."""
        mock_bedrock = MagicMock()
        mock_boto.return_value = mock_bedrock
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps({
                    "content": [
                        {"type": "text", "text": "I'll help you"},
                        {
                            "type": "tool_use",
                            "id": "tool-123",
                            "name": "get_balance",
                            "input": {"account_id": "acc-1"}
                        }
                    ],
                    "stop_reason": "tool_use"
                }).encode()
            )
        }

        client = ClaudeClient()
        tools = [{"name": "get_balance", "description": "Get balance", "input_schema": {}}]
        result = client.invoke_with_tools("Check balance", tools)

        assert result["text"] == "I'll help you"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "get_balance"

    def test_lazy_client_initialization(self):
        """Test Bedrock client is lazily initialized."""
        client = ClaudeClient()
        assert client._client is None

        with patch("boto3.client") as mock_boto:
            _ = client.client
            mock_boto.assert_called_once()
