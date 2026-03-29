from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class Message(BaseModel):
    sender: str
    text: str
    timestamp: Union[int, str]


class HybridMetadata(BaseModel):
    deceptionNarrative: Optional[str] = None
    availableSurfaces: List[str] = []
    orchestrationMetadata: Dict[str, Any] = {}
    temporaryConstraintOverrides: Dict[str, Any] = {}
    promptMediationHints: Dict[str, Any] = {}
    externalPersonaHints: Dict[str, Any] = {}
    externalArtifactFocus: List[str] = []
    deceptionLayerTraceId: Optional[str] = None
    externalLayerVersion: Optional[str] = None

class EvaluationRequest(BaseModel):
    message: Message
    conversationHistory: List[Message] = []
    metadata: Dict[str, Any] = {}
    hybridMetadata: Optional[HybridMetadata] = None

class EvaluationResponse(BaseModel):
    sessionId: str
    behaviorState: str = Field(..., description="Current FSM state")
    activeConstraint: str = Field(..., description="The current intent or behavioral constraint")
    evasionScore: float = 0.0
    exhaustionScore: float = 0.0
    recommendation: Optional[str] = None
    terminate: bool = False
    reason: Optional[str] = None
    reply: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BehaviorTrajectoryEntry(BaseModel):
    turnIndex: int
    behaviorState: str
    activeConstraint: str
    timestampMs: int

class BehaviorTrajectoryResponse(BaseModel):
    sessionId: str
    trajectory: List[BehaviorTrajectoryEntry]


class SessionStateUpdate(BaseModel):
    message: Message
    metadata: Dict[str, Any] = {}
    hybridMetadata: Optional[HybridMetadata] = None

class DeliveryTask(BaseModel):
    taskId: str
    sessionId: str
    reportPayload: Dict[str, Any]
    destinationUrl: str
    retryCount: int = 0

