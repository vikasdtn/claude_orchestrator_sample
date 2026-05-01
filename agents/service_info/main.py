"""FastAPI server for Service Info Agent."""

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.models import AgentRequest, AgentResponse, Priority
from .agent import ServiceInfoAgent

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
agent: ServiceInfoAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = ServiceInfoAgent()
    yield
    if agent:
        agent.gateway.close()


app = FastAPI(title="Service Info Agent", version="1.0.0", lifespan=lifespan)


class ProcessRequest(BaseModel):
    query: str
    customer_id: str | None = None
    priority: str = "medium"
    context: dict = {}


@app.get("/health")
async def health_check():
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return await agent.health_check()


@app.post("/process", response_model=AgentResponse)
async def process_query(request: ProcessRequest):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    agent_request = AgentRequest(
        request_id=str(uuid.uuid4()),
        query=request.query,
        customer_id=request.customer_id,
        priority=Priority(request.priority),
        context=request.context,
    )
    return await agent.process_request(agent_request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
