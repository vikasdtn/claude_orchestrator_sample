"""FastAPI server for the Orchestrator Agent."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from shared.models import OrchestratorPayload, OrchestratorResponse, Priority, SecurityVerificationResponse
from .agent import OrchestratorAgent

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

orchestrator: OrchestratorAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator
    orchestrator = OrchestratorAgent()
    logger.info("Orchestrator agent initialized")
    yield
    if orchestrator:
        await orchestrator.close()
    logger.info("Orchestrator agent shutdown")


app = FastAPI(
    title="Contact Centre Orchestrator Agent",
    description="Super Agent that uses Claude to orchestrate utility agents",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return await orchestrator.health_check()


@app.post("/process", response_model=OrchestratorResponse)
async def process_intent(payload: OrchestratorPayload):
    """Process a customer intent through the orchestrator.
    
    This endpoint receives payloads from Lambda containing:
    - customer_id: Customer account identifier
    - intent: Customer's query or request
    - session_id: Optional session tracking ID
    - priority: Request priority level
    - metadata: Additional context
    
    The orchestrator:
    1. Uses Claude to analyze the intent and create an execution plan
    2. Sends the plan to the external security agent for verification
    3. Only executes the plan if security approves
    4. Invokes appropriate utility agents
    5. Synthesizes responses into a coherent reply
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    logger.info(f"Received intent from customer {payload.customer_id}: {payload.intent[:100]}...")
    
    response = await orchestrator.process_payload(payload)
    
    if response.blocked_by_security:
        logger.warning(f"Request {response.request_id} blocked by security agent")
    
    return response


@app.get("/agents")
async def list_agents():
    """List available utility agents."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    from .agent import AGENT_ENDPOINTS
    return {
        "agents": {
            agent_type.value: endpoint 
            for agent_type, endpoint in AGENT_ENDPOINTS.items()
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
