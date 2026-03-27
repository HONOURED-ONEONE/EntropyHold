from fastapi import APIRouter, Depends, HTTPException, Header
from app.settings import settings
from app.store.session_repo import load_session
from app.store.redis_conn import get_redis
import app.observability.metrics as metrics

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(x_admin_key: str = Header(default="", alias="x-admin-key")):
    if not settings.ADMIN_RBAC_ENABLED:
        return
    # Secure default: if enabled but no key configured, reject all.
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access disabled (no key configured)")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

@router.get("/session/{session_id}")
def get_session_snapshot(session_id: str, _=Depends(require_admin)):
    """Compact session snapshot for admin dashboard."""
    s = load_session(session_id)
    # CQ: Questions asked, relevant, redflags, elicitation
    cq = {
        "questionsAsked": int(getattr(s, "cqQuestionsAsked", 0) or 0),
        "relevantQuestions": int(getattr(s, "cqRelevantQuestions", 0) or 0),
        "redFlagMentions": int(getattr(s, "cqRedFlagMentions", 0) or 0),
        "elicitationAttempts": int(getattr(s, "cqElicitationAttempts", 0) or 0),
    }
    
    return {
        "sessionId": s.sessionId,
        "state": s.state,
        "scamDetected": bool(s.scamDetected),
        "scamType": s.scamType or "UNKNOWN",
        "confidence": float(getattr(s, "confidence", 0.0) or 0.0),
        "finalizedAt": s.finalizedAt,
        "reportId": s.reportId,
        "callbackStatus": s.callbackStatus,
        "cq": cq,
        "outboxLedger": s.outboxEntry or {},
        "turnsEngaged": int(getattr(s, "turnsEngaged", 0) or 0),
        "durationSec": int(getattr(s, "engagementDurationSeconds", 0) or 0),
    }

@router.get("/session/{session_id}/timeline")
def get_session_timeline(session_id: str, _=Depends(require_admin)):
    """Ordered event stream for the session."""
    s = load_session(session_id)
    events = []
    
    # Conversation events
    for m in s.conversation or []:
        events.append({
            "timestamp": m.get("timestamp"),
            "type": "message",
            "sender": m.get("sender"),
            "content": m.get("text")
        })
        
    # Postscript events (latched)
    for p in s.postscript or []:
         events.append({
            "timestamp": p.get("timestamp"),
            "type": "postscript_message",
            "sender": p.get("sender"),
            "content": p.get("text"),
            "ignored": True
         })
    
    # Finalization event
    if s.finalizedAt:
        events.append({
            "timestamp": s.finalizedAt,
            "type": "lifecycle_finalized",
            "reportId": s.reportId,
            "reason": (s.agentNotes or "").split("|")[-1].strip() if "finalize_reason=" in (s.agentNotes or "") else "unknown"
        })
        
    # Sort by timestamp
    return sorted(events, key=lambda x: int(x.get("timestamp", 0) or 0))

@router.get("/callbacks")
def get_callbacks(session_id: str, _=Depends(require_admin)):
    """View the idempotency ledger for a session."""
    s = load_session(session_id)
    return {
        "sessionId": session_id,
        "callbackStatus": s.callbackStatus,
        "outboxLedger": s.outboxEntry or {},
        "finalReportPreview": s.finalReport
    }

@router.get("/slo")
def get_slo(_=Depends(require_admin)):
    """
    Observability snapshot backed by Redis counters.
    """
    return metrics.get_slo_snapshot()

@router.get("/session/{session_id}/behavior")
def get_session_behavior(session_id: str, _=Depends(require_admin)):
    """Behavioral analysis snapshot for a session."""
    from app.core.orchestrator import get_behavior_state
    state = get_behavior_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state

@router.get("/session/{session_id}/trajectory")
def get_session_trajectory(session_id: str, _=Depends(require_admin)):
    """Full trajectory of behavioral states and constraints."""
    s = load_session(session_id)
    if not s.trajectory:
        raise HTTPException(status_code=404, detail="No trajectory recorded for this session")
    return {
        "sessionId": s.sessionId,
        "trajectory": s.trajectory
    }

@router.get("/hybrid/status")
def get_hybrid_status(_=Depends(require_admin)):
    """High-level snapshot of hybrid configuration and metrics."""
    r = get_redis()
    return {
        "external_reporting_mode": settings.EXTERNAL_REPORTING_MODE,
        "behavior_evaluations_total": int(r.get(metrics.K_BEH_EVAL) or 0),
        "hybrid_overlay_applied_total": int(r.get(metrics.K_HYB_OVERLAY) or 0),
        "reporting_externalized_total": int(r.get(metrics.K_REP_EXT) or 0),
        "slo": metrics.get_slo_snapshot()
    }
