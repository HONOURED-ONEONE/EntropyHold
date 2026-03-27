from fastapi import FastAPI, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import httpx
import logging

# We define local copies or import from shared contracts
from contracts.models import EvaluationRequest, EvaluationResponse, SessionStateUpdate

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
    logger.info(f"Evaluating trigger for session {request.session_id}")
    
    # Policy / rules-of-engagement check placeholder
    if request.trigger_type == "banned_actor":
        raise HTTPException(status_code=403, detail="Policy violation: Actor is banned.")
    
    # Enrich with external layer metadata (e.g., prompt mediation overrides)
    request.external_metadata = request.external_metadata or {}
    request.external_metadata["orchestrator_node"] = "us-east-1"
    
    try:
        # Call the Python Behavioral Brain (HTTP)
        # Note: Do NOT reimplement behavioral heuristics locally
        response = await client.post("/api/internal/evaluate", json=request.dict())
        response.raise_for_status()
        return EvaluationResponse(**response.json())
    except httpx.HTTPError as e:
        logger.error(f"Error calling Python brain: {e}")
        # Return fallback or raise
        raise HTTPException(status_code=502, detail="Behavioral Brain unavailable")

@app.post("/api/orchestration/session/{session_id}/update")
async def update_session(
    session_id: str,
    update: SessionStateUpdate,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    try:
        response = await client.post(f"/api/internal/session/{session_id}/update", json=update.dict())
        response.raise_for_status()
        return {"status": "updated"}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="Behavioral Brain unavailable")

@app.get("/api/orchestration/session/{session_id}")
async def get_session(
    session_id: str,
    client: httpx.AsyncClient = Depends(get_brain_client),
    authorized: bool = Depends(check_auth)
):
    try:
        response = await client.get(f"/api/internal/session/{session_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=404, detail="Session not found in Brain")
