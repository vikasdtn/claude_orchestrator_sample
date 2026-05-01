"""Tests for Orchestrator Agent with security verification."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from shared.models import (
    AgentType,
    OrchestratorPayload,
    Priority,
    RiskLevel,
    SecurityVerificationResponse,
)


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent."""

    @pytest.fixture
    def orchestrator(self, mock_gateway, mock_claude):
        """Create orchestrator instance with mocks."""
        with patch.dict("os.environ", {
            "AWS_REGION": "us-east-1",
            "SKIP_SECURITY_VERIFICATION": "true",
        }):
            from orchestrator.agent import OrchestratorAgent
            return OrchestratorAgent(
                gateway_client=mock_gateway,
                claude_client=mock_claude,
            )

    @pytest.fixture
    def sample_payload(self):
        """Create a sample orchestrator payload."""
        return OrchestratorPayload(
            customer_id="cust-123",
            intent="What is my account balance?",
            priority=Priority.MEDIUM,
        )

    def test_init(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.gateway is not None
        assert orchestrator.claude is not None

    @pytest.mark.asyncio
    async def test_process_payload_creates_plan(self, orchestrator, sample_payload):
        """Test that processing payload creates an execution plan."""
        response = await orchestrator.process_payload(sample_payload)
        
        assert response.customer_id == sample_payload.customer_id
        assert response.intent == sample_payload.intent
        assert response.execution_plan is not None

    @pytest.mark.asyncio
    async def test_process_payload_includes_security_verification(
        self, orchestrator, sample_payload
    ):
        """Test that response includes security verification."""
        response = await orchestrator.process_payload(sample_payload)
        
        # With SKIP_SECURITY_VERIFICATION=true, should still have verification
        assert response.security_verification is not None
        assert response.security_verification.approved is True


class TestSecurityVerification:
    """Tests for security verification flow."""

    @pytest.fixture
    def orchestrator_with_security(self, mock_gateway, mock_claude):
        """Create orchestrator with security verification enabled."""
        with patch.dict("os.environ", {
            "AWS_REGION": "us-east-1",
            "SKIP_SECURITY_VERIFICATION": "false",
            "SECURITY_AGENT_URL": "http://mock-security:8080",
        }):
            from orchestrator.agent import OrchestratorAgent
            return OrchestratorAgent(
                gateway_client=mock_gateway,
                claude_client=mock_claude,
            )

    @pytest.fixture
    def sample_payload(self):
        return OrchestratorPayload(
            customer_id="cust-123",
            intent="What is my account balance?",
            priority=Priority.MEDIUM,
        )

    @pytest.mark.asyncio
    async def test_security_approval_allows_execution(
        self, orchestrator_with_security, sample_payload
    ):
        """Test that approved plans are executed."""
        # Mock security agent approval
        with patch.object(
            orchestrator_with_security._http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "request_id": "test-123",
                "approved": True,
                "risk_level": "low",
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = await orchestrator_with_security.process_payload(sample_payload)
            
            assert response.blocked_by_security is False
            assert response.security_verification.approved is True

    @pytest.mark.asyncio
    async def test_security_denial_blocks_execution(
        self, orchestrator_with_security, sample_payload
    ):
        """Test that denied plans are not executed."""
        with patch.object(
            orchestrator_with_security._http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "request_id": "test-123",
                "approved": False,
                "risk_level": "high",
                "denial_reason": "Suspicious activity detected",
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = await orchestrator_with_security.process_payload(sample_payload)
            
            assert response.blocked_by_security is True
            assert response.success is False
            assert response.agent_responses == []
            assert "security" in response.escalation_reason.lower()

    @pytest.mark.asyncio
    async def test_security_timeout_fails_closed(
        self, orchestrator_with_security, sample_payload
    ):
        """Test that security timeout denies execution (fail closed)."""
        with patch.object(
            orchestrator_with_security._http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            response = await orchestrator_with_security.process_payload(sample_payload)
            
            assert response.blocked_by_security is True
            assert response.security_verification.approved is False
            assert "timed out" in response.security_verification.denial_reason.lower()

    @pytest.mark.asyncio
    async def test_security_modified_plan_used(
        self, orchestrator_with_security, sample_payload
    ):
        """Test that modified plan from security agent is used."""
        with patch.object(
            orchestrator_with_security._http_client,
            "post",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "request_id": "test-123",
                "approved": True,
                "risk_level": "medium",
                "modified_plan": {
                    "plan_id": "modified-plan",
                    "customer_id": "cust-123",
                    "intent": "What is my account balance?",
                    "steps": [
                        {
                            "step_number": 1,
                            "agent_type": "faq",
                            "instruction": "Modified instruction",
                            "depends_on": [],
                            "reason": "Security modified",
                        }
                    ],
                    "estimated_complexity": "low",
                    "requires_human_review": False,
                },
                "restrictions": ["no_account_changes"],
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            response = await orchestrator_with_security.process_payload(sample_payload)
            
            assert response.execution_plan.plan_id == "modified-plan"
            assert response.security_verification.restrictions == ["no_account_changes"]


class TestFallbackPlan:
    """Tests for fallback execution plan."""

    @pytest.fixture
    def orchestrator(self, mock_gateway, mock_claude):
        with patch.dict("os.environ", {
            "AWS_REGION": "us-east-1",
            "SKIP_SECURITY_VERIFICATION": "true",
        }):
            from orchestrator.agent import OrchestratorAgent
            return OrchestratorAgent(
                gateway_client=mock_gateway,
                claude_client=mock_claude,
            )

    @pytest.mark.parametrize("intent,expected_agent", [
        ("What is my bill?", AgentType.BILLING),
        ("Is there an outage?", AgentType.KNOWN_OUTAGES),
        ("Check my ticket status", AgentType.TICKET_UPDATES),
        ("I want to buy something", AgentType.SALES),
        ("Update my email", AgentType.ACCOUNT_ADMIN),
    ])
    def test_fallback_plan_keyword_detection(self, orchestrator, intent, expected_agent):
        """Test fallback plan keyword detection."""
        payload = OrchestratorPayload(customer_id="cust-123", intent=intent)
        plan = orchestrator._create_fallback_plan(payload, "req-123")
        
        agent_types = [step.agent_type for step in plan.steps]
        assert expected_agent in agent_types

    def test_fallback_plan_defaults_to_faq(self, orchestrator):
        """Test fallback plan defaults to FAQ."""
        payload = OrchestratorPayload(customer_id="cust-123", intent="xyz random")
        plan = orchestrator._create_fallback_plan(payload, "req-123")
        
        assert plan.steps[0].agent_type == AgentType.FAQ
