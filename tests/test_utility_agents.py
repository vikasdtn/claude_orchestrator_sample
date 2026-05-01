"""Tests for utility agents with Claude-powered tool selection."""

import pytest
from unittest.mock import MagicMock, patch

from shared.models import AgentRequest, AgentType, Priority, ToolResult


class TestBillingAgent:
    """Tests for BillingAgent."""

    @pytest.fixture
    def agent(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            from agents.billing.agent import BillingAgent
            return BillingAgent(gateway_client=mock_gateway, claude_client=mock_claude)

    def test_init(self, agent):
        assert agent.agent_type == AgentType.BILLING

    def test_available_tools_defined(self, agent):
        tools = agent.available_tools
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_account_balance" in tool_names
        assert "get_invoices" in tool_names

    def test_execute_tool_get_balance(self, agent, mock_gateway):
        result = agent.execute_tool("get_account_balance", {"account_id": "acc-123"})
        mock_gateway.get_billing_info.assert_called_with("acc-123")

    def test_escalation_keywords_dispute(self, agent, sample_request):
        sample_request.query = "I want to dispute this charge"
        needs_escalation, reason = agent._check_escalation(sample_request, "", [])
        assert needs_escalation is True
        assert "dispute" in reason.lower()

    def test_escalation_keywords_refund(self, agent, sample_request):
        sample_request.query = "I need a refund"
        needs_escalation, reason = agent._check_escalation(sample_request, "", [])
        assert needs_escalation is True


class TestTechnicalSupportAgent:
    """Tests for TechnicalSupportAgent."""

    @pytest.fixture
    def agent(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            from agents.technical_support.agent import TechnicalSupportAgent
            return TechnicalSupportAgent(gateway_client=mock_gateway, claude_client=mock_claude)

    def test_init(self, agent):
        assert agent.agent_type == AgentType.TECHNICAL_SUPPORT

    def test_available_tools_defined(self, agent):
        tools = agent.available_tools
        tool_names = [t["name"] for t in tools]
        assert "search_troubleshooting_guides" in tool_names
        assert "run_diagnostic" in tool_names
        assert "create_support_ticket" in tool_names

    def test_execute_tool_search_guides(self, agent, mock_gateway):
        agent.execute_tool("search_troubleshooting_guides", {"issue": "connection problem"})
        mock_gateway.search_confluence.assert_called()

    def test_escalation_urgent_keyword(self, agent, sample_request):
        sample_request.query = "URGENT: Everything is down!"
        needs_escalation, reason = agent._check_escalation(sample_request, "", [])
        assert needs_escalation is True


class TestProductInfoAgent:
    """Tests for ProductInfoAgent."""

    @pytest.fixture
    def agent(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            from agents.product_info.agent import ProductInfoAgent
            return ProductInfoAgent(gateway_client=mock_gateway, claude_client=mock_claude)

    def test_init(self, agent):
        assert agent.agent_type == AgentType.PRODUCT_INFO

    def test_available_tools_defined(self, agent):
        tools = agent.available_tools
        tool_names = [t["name"] for t in tools]
        assert "search_product_docs" in tool_names
        assert "get_product_pricing" in tool_names


class TestAccountAdminAgent:
    """Tests for AccountAdminAgent."""

    @pytest.fixture
    def agent(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            from agents.account_admin.agent import AccountAdminAgent
            return AccountAdminAgent(gateway_client=mock_gateway, claude_client=mock_claude)

    def test_init(self, agent):
        assert agent.agent_type == AgentType.ACCOUNT_ADMIN

    def test_escalation_close_account(self, agent, sample_request):
        sample_request.query = "I want to close my account"
        needs_escalation, reason = agent._check_escalation(sample_request, "", [])
        assert needs_escalation is True
        assert "close" in reason.lower()


class TestFAQAgent:
    """Tests for FAQAgent."""

    @pytest.fixture
    def agent(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            from agents.faq.agent import FAQAgent
            return FAQAgent(gateway_client=mock_gateway, claude_client=mock_claude)

    def test_init(self, agent):
        assert agent.agent_type == AgentType.FAQ

    def test_execute_tool_search_kb(self, agent, mock_gateway):
        agent.execute_tool("search_knowledge_base", {"query": "how to reset password"})
        mock_gateway.search_confluence.assert_called()
