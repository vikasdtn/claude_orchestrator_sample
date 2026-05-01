"""Tests for shared models."""

import pytest
from datetime import datetime

from shared.models import (
    AgentRequest,
    AgentResponse,
    AgentType,
    CustomerContext,
    Priority,
    ToolCall,
    ToolResult,
)


class TestAgentRequest:
    """Tests for AgentRequest model."""

    def test_create_minimal_request(self):
        """Test creating request with minimal fields."""
        request = AgentRequest(
            request_id="req-001",
            query="What is my balance?",
        )
        assert request.request_id == "req-001"
        assert request.query == "What is my balance?"
        assert request.priority == Priority.MEDIUM
        assert request.context == {}

    def test_create_full_request(self):
        """Test creating request with all fields."""
        request = AgentRequest(
            request_id="req-002",
            query="Check my ticket status",
            customer_id="cust-123",
            session_id="sess-456",
            priority=Priority.HIGH,
            context={"previous_agent": "faq"},
        )
        assert request.customer_id == "cust-123"
        assert request.session_id == "sess-456"
        assert request.priority == Priority.HIGH
        assert request.context["previous_agent"] == "faq"

    def test_request_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        request = AgentRequest(request_id="req-003", query="Test")
        assert isinstance(request.timestamp, datetime)


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_create_successful_response(self):
        """Test creating a successful response."""
        response = AgentResponse(
            request_id="req-001",
            agent_type="billing",
            success=True,
            response="Your balance is $50.00",
        )
        assert response.success is True
        assert response.requires_escalation is False
        assert response.confidence == 1.0

    def test_create_escalation_response(self):
        """Test creating a response requiring escalation."""
        response = AgentResponse(
            request_id="req-002",
            agent_type="technical_support",
            success=True,
            response="Issue requires specialist attention",
            requires_escalation=True,
            escalation_reason="Complex technical issue",
            confidence=0.4,
        )
        assert response.requires_escalation is True
        assert response.escalation_reason == "Complex technical issue"
        assert response.confidence == 0.4


class TestToolCall:
    """Tests for ToolCall model."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        tool_call = ToolCall(
            tool_name="salesforce_query",
            parameters={"query": "SELECT Id FROM Account"},
            timeout_seconds=60,
        )
        assert tool_call.tool_name == "salesforce_query"
        assert tool_call.timeout_seconds == 60

    def test_default_timeout(self):
        """Test default timeout value."""
        tool_call = ToolCall(tool_name="test_tool", parameters={})
        assert tool_call.timeout_seconds == 30


class TestToolResult:
    """Tests for ToolResult model."""

    def test_successful_result(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_name="confluence_search",
            success=True,
            result={"pages": [{"id": "123", "title": "FAQ"}]},
            execution_time_ms=150,
        )
        assert result.success is True
        assert result.error is None
        assert result.execution_time_ms == 150

    def test_failed_result(self):
        """Test failed tool result."""
        result = ToolResult(
            tool_name="billing_query",
            success=False,
            error="Connection timeout",
            execution_time_ms=30000,
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestAgentType:
    """Tests for AgentType enum."""

    def test_all_agent_types_defined(self):
        """Test all expected agent types are defined."""
        expected_types = [
            "product_info",
            "faq",
            "known_outages",
            "service_info",
            "ticket_updates",
            "billing",
            "sales",
            "technical_support",
            "account_admin",
        ]
        for agent_type in expected_types:
            assert AgentType(agent_type) is not None


class TestCustomerContext:
    """Tests for CustomerContext model."""

    def test_create_minimal_context(self):
        """Test creating context with minimal fields."""
        context = CustomerContext(customer_id="cust-001")
        assert context.customer_id == "cust-001"
        assert context.is_authenticated is False

    def test_create_full_context(self):
        """Test creating context with all fields."""
        context = CustomerContext(
            customer_id="cust-002",
            account_number="ACC-12345",
            name="Test Customer",
            email="test@example.com",
            phone="+1234567890",
            account_type="premium",
            is_authenticated=True,
        )
        assert context.is_authenticated is True
        assert context.account_type == "premium"
