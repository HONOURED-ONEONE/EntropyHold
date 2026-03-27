from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

Sender = Literal["scammer", "user"]

class Message(BaseModel):
    sender: Sender
    text: str
    # PDF examples use epoch ms; field description mentions ISO-8601.
    timestamp: Union[int, str]

class Metadata(BaseModel):
    channel: Optional[str] = None  # SMS / WhatsApp / Email / Chat
    language: Optional[str] = None
    locale: Optional[str] = None

class HybridMetadata(BaseModel):
    deceptionNarrative: Optional[str] = Field(None, description="Global narrative provided by external layer")
    availableSurfaces: List[str] = Field(default_factory=list, description="Available deception surfaces/tools")
    orchestrationMetadata: Dict[str, Any] = Field(default_factory=dict)
    temporaryConstraintOverrides: Dict[str, Any] = Field(default_factory=dict)
    promptMediationHints: Dict[str, Any] = Field(default_factory=dict)
    externalPersonaHints: Dict[str, Any] = Field(default_factory=dict)
    externalArtifactFocus: List[str] = Field(default_factory=list)
    deceptionLayerTraceId: Optional[str] = None
    externalLayerVersion: Optional[str] = None

class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = Field(default_factory=list)
    detection: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    # ✅ Hybrid/External Layer integration
    hybridMetadata: Optional[HybridMetadata] = None

class HoneypotResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    reply: str

# --- Behavioral Brain API Schemas ---

class BehaviorStateResponse(BaseModel):
    sessionId: str
    behaviorState: str = Field(..., description="Current FSM state (e.g., BF_S3)")
    activeConstraint: str = Field(..., description="The current intent or behavioral constraint")
    evasionScore: float = Field(default=0.0, ge=0.0, le=1.0)
    exhaustionScore: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendation: Optional[str] = None
    terminate: bool = False
    reason: Optional[str] = None
    reply: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BehaviorEvaluateRequest(BaseModel):
    message: Message
    conversationHistory: List[Message] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    hybridMetadata: Optional[HybridMetadata] = None

class BehaviorUpdateRequest(BaseModel):
    message: Message
    metadata: Optional[Dict[str, Any]] = None
    hybridMetadata: Optional[HybridMetadata] = None

class BehaviorTrajectoryEntry(BaseModel):
    turnIndex: int
    behaviorState: str
    activeConstraint: str
    timestampMs: int

class BehaviorTrajectoryResponse(BaseModel):
    sessionId: str
    trajectory: List[BehaviorTrajectoryEntry]