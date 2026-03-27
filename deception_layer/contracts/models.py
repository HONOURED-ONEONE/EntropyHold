from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class EvaluationRequest(BaseModel):
    session_id: str
    trigger_type: str
    payload: Dict[str, Any]
    policy_overrides: Optional[Dict[str, Any]] = None
    external_metadata: Optional[Dict[str, Any]] = None

class EvaluationResponse(BaseModel):
    session_id: str
    action: str
    prompt_mediation: Optional[Dict[str, Any]] = None
    brain_version: str

class SessionStateUpdate(BaseModel):
    session_id: str
    state: str
    trajectory: List[str]
    last_updated: datetime

class DeliveryTask(BaseModel):
    task_id: str
    session_id: str
    report_payload: Dict[str, Any]
    destination_url: str
    retry_count: int = 0
