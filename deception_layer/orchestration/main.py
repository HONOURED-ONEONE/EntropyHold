from fastapi import FastAPI, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import httpx
import logging

# We define local copies or import from shared contracts
from contracts.models import EvaluationRequest, EvaluationResponse, SessionStateUpdate, BehaviorTrajectoryResponse, HybridMetadata

app = FastAPI(title="Deception Layer Orchestration API", version="1.0.0")
logger = logging.getLogger(__name__)

BRAIN_URL = "http://python-brain:8000" # Placeholder for Python Behavioral Brain

async def get_brain_client():
    async with httpx.AsyncClient(base_url=BRAIN_URL) as client:
        yield client

def check_auth(token: str = "placeholder"):
    # Auth/Authz placeholder for incoming triggers
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/api/orchestration/health")
async def health_check():
    return {"status": "ok", "service": "orchestration"}

@app.post("/api/orchestration/evaluate", response_model=EvaluationResponse)
async def evaluate_trigger(
    request: EvaluationRequest,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    """
    Accept suspicious activity / engagement trigger requests.
    Validates orchestration context, applies policy checks, enriches requests, and calls the Python Behavioral Brain.
    """
    # 1) Local Policy Enforcement
    # Example: Banned actors or known malicious signatures
    # (Matches test_evaluate_trigger_banned expectations)
    try:
        if request.metadata.get("trigger_type") == "banned_actor":
             raise HTTPException(status_code=403, detail="Policy violation: banned actor")
    except AttributeError:
        # In case request.metadata is not a dict or missing
        pass

    # 2) Enrichment with external layer metadata
    if not request.hybridMetadata:
        request.hybridMetadata = HybridMetadata()
    
    if not request.hybridMetadata.orchestrationMetadata:
        request.hybridMetadata.orchestrationMetadata = {}

    request.hybridMetadata.orchestrationMetadata["orchestrator_node"] = "us-east-1"
    request.hybridMetadata.externalLayerVersion = "1.0.0"
    
    try:
        # Call the Python Behavioral Brain (HTTP)
        # Endpoint: /behavior/evaluate (stateless)
        response = await client.post("/behavior/evaluate", json=request.dict())
        response.raise_for_status()
        return EvaluationResponse(**response.json())
    except httpx.HTTPError as e:
        logger.error(f"Error calling Python brain: {e}")
        raise HTTPException(status_code=502, detail="Behavioral Brain unavailable")

@app.post("/api/orchestration/session/{session_id}/update", response_model=EvaluationResponse)
async def update_session(
    session_id: str,
    update: SessionStateUpdate,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    """Advancing an existing session in the Behavioral Brain."""
    try:
        # Endpoint: /behavior/session/{session_id}/update (stateful)
        response = await client.post(f"/behavior/session/{session_id}/update", json=update.dict())
        response.raise_for_status()
        return EvaluationResponse(**response.json())
    except httpx.HTTPError as e:
        logger.error(f"Error updating session in brain: {e}")
        raise HTTPException(status_code=502, detail="Behavioral Brain unavailable")

@app.get("/api/orchestration/session/{session_id}/state", response_model=EvaluationResponse)
async def get_session_state(
    session_id: str,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    """Retrieve current state of a session from the Behavioral Brain."""
    try:
        # Endpoint: /behavior/session/{session_id}/state
        response = await client.get(f"/behavior/session/{session_id}/state")
        response.raise_for_status()
        return EvaluationResponse(**response.json())
    except httpx.HTTPError as e:
        logger.error(f"Error fetching session state: {e}")
        raise HTTPException(status_code=404, detail="Session not found in Brain")

@app.get("/api/orchestration/session/{session_id}/trajectory", response_model=BehaviorTrajectoryResponse)
async def get_session_trajectory(
    session_id: str,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    """Retrieve trajectory of a session from the Behavioral Brain."""
    try:
        # Endpoint: /behavior/session/{session_id}/trajectory
        response = await client.get(f"/behavior/session/{session_id}/trajectory")
        response.raise_for_status()
        return BehaviorTrajectoryResponse(**response.json())
    except httpx.HTTPError as e:
        logger.error(f"Error fetching session trajectory: {e}")
        raise HTTPException(status_code=404, detail="Session not found in Brain")


