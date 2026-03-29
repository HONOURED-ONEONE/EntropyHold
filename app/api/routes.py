import json
from typing import Any, List

from fastapi import APIRouter, Depends, Body, Request, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.schemas import (
    HoneypotRequest, HoneypotResponse,
    BehaviorStateResponse, BehaviorEvaluateRequest, BehaviorUpdateRequest,
    BehaviorTrajectoryResponse, BehaviorTrajectoryEntry
)
from app.api.auth import require_api_key
from app.core.orchestrator import handle_event, get_behavior_state
from app.api.normalize import normalize_honeypot_payload
from app.settings import settings
from app.intel.artifact_registry import snapshot_intent_map, reload_intent_map
from app.store.redis_conn import get_redis
from app.store.session_repo import load_session

router = APIRouter()

COMPAT_POST_PATHS = (
    "/api/honeypot",     # primary
    "/honeypot",         # common alias
    "/detect",           # evaluator example path style
    "/api/detect",       # extra safety
)

async def _handle_honeypot(request: Request, payload: Any) -> HoneypotResponse:
    """Accept ANY payload (or no payload) and normalize into HoneypotRequest."""

    # If body missing or couldn't be parsed into payload, try reading it manually
    if payload is None:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    # If payload is not a dict, wrap or ignore
    if not isinstance(payload, dict):
        if isinstance(payload, str):
            payload = {"message": payload}
        else:
            payload = {}

    normalized = normalize_honeypot_payload(payload)
    # req = HoneypotRequest.model_validate(normalized) # old pydantic v1 vs v2 check
    # We'll just pass the dict for now as handle_event expects an object with attributes or we can wrap it
    class Obj:
        def __init__(self, **entries):
            self.__dict__.update(entries)
    
    # handle_event expects an object with .sessionId, .message, .conversationHistory etc.
    # We can create a simple Namespace object
    from argparse import Namespace
    msg_obj = Namespace(**normalized.get("message", {}))
    req_obj = Namespace(
        sessionId=normalized.get("sessionId"),
        message=msg_obj,
        conversationHistory=normalized.get("conversationHistory", []),
        metadata=normalized.get("metadata", {}),
        settings=normalized.get("settings", {}),
        hybridMetadata=normalized.get("hybridMetadata")
    )

    out = await run_in_threadpool(handle_event, req_obj)

    reply_val = ""
    if isinstance(out, dict):
        reply_val = out.get("reply") or ""
    else:
        reply_val = str(out)

    return HoneypotResponse(status="success", reply=reply_val)


def _ping_reply() -> HoneypotResponse:
    return HoneypotResponse(
        status="success",
        reply="Honeypot API is running. Send a POST request with {sessionId, message, conversationHistory, metadata}."
    )

# --- Compatibility Endpoints ---

for _path in COMPAT_POST_PATHS:
    @router.post(_path, response_model=HoneypotResponse, dependencies=[Depends(require_api_key)])
    async def honeypot_post(request: Request, payload: Any = Body(None)):
        return await _handle_honeypot(request, payload)

    @router.get(_path, response_model=HoneypotResponse, dependencies=[Depends(require_api_key)])
    async def honeypot_get():
        return _ping_reply()

@router.api_route("/", methods=["POST"], response_model=HoneypotResponse, dependencies=[Depends(require_api_key)])
async def honeypot_root(request: Request, payload: Any = Body(None)):
    return await _handle_honeypot(request, payload)

@router.get("/ping", response_model=HoneypotResponse, dependencies=[Depends(require_api_key)])
async def ping():
    return _ping_reply()


# --- New Behavioral Brain API ---

@router.post("/behavior/evaluate", response_model=BehaviorStateResponse)
async def behavior_evaluate(payload: BehaviorEvaluateRequest = Body(...)):
    """
    Stateless evaluation of a message/history to determine behavioral cues.
    """
    import uuid
    from argparse import Namespace
    temp_session_id = f"eval-{uuid.uuid4()}"
    
    msg_obj = Namespace(**payload.message.dict())
    req_obj = Namespace(
        sessionId=temp_session_id,
        message=msg_obj,
        conversationHistory=[m.dict() for m in payload.conversationHistory],
        metadata=payload.metadata or {},
        settings={"ephemeral": True},
        hybridMetadata=payload.hybridMetadata.dict() if payload.hybridMetadata else None
    )
    
    result = await run_in_threadpool(handle_event, req_obj)
    return BehaviorStateResponse(sessionId=temp_session_id, **result)


@router.post("/behavior/session/{session_id}/update", response_model=BehaviorStateResponse)
async def behavior_update(session_id: str, payload: BehaviorUpdateRequest = Body(...)):
    """
    Stateful update that advances the behavior engine.
    """
    from argparse import Namespace
    msg_obj = Namespace(**payload.message.dict())
    req_obj = Namespace(
        sessionId=session_id,
        message=msg_obj,
        conversationHistory=[],
        detection={},
        metadata=payload.metadata or {},
        settings={},
        hybridMetadata=payload.hybridMetadata.dict() if payload.hybridMetadata else None
    )

    result = await run_in_threadpool(handle_event, req_obj)
    return BehaviorStateResponse(sessionId=session_id, **result)


@router.get("/behavior/session/{session_id}/state", response_model=BehaviorStateResponse)
async def behavior_get_state_route(session_id: str):
    state = await run_in_threadpool(get_behavior_state, session_id=session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return BehaviorStateResponse(**state)


@router.get("/behavior/session/{session_id}/trajectory", response_model=BehaviorTrajectoryResponse)
async def behavior_get_trajectory_route(session_id: str):
    session = await run_in_threadpool(load_session, session_id=session_id)
    # If the session has no conversation/trajectory, we can consider it empty
    if not session.conversation and not session.trajectory:
        raise HTTPException(status_code=404, detail="Session not found")
    
    trajectory = [BehaviorTrajectoryEntry(**t) for t in session.trajectory]
    return BehaviorTrajectoryResponse(sessionId=session_id, trajectory=trajectory)


# --- Debug Endpoints ---

@router.get("/debug/feature-flags")
def debug_feature_flags(_=Depends(require_api_key)):
    return {
        "BF_LLM_REPHRASE": bool(settings.BF_LLM_REPHRASE),
        "INTENT_MAP_REFRESH_SEC": int(settings.INTENT_MAP_REFRESH_SEC),
        "REGISTRY_INTENT_MAP_KEY": settings.REGISTRY_INTENT_MAP_KEY,
        "EXTERNAL_REPORTING_MODE": settings.EXTERNAL_REPORTING_MODE,
        "ENABLE_OUTBOX": settings.ENABLE_OUTBOX,
        "ENABLE_GUVI_CALLBACK": settings.ENABLE_GUVI_CALLBACK,
    }

@router.get("/debug/behavior/session/{session_id}")
async def debug_behavior_session(session_id: str, _=Depends(require_api_key)):
    """In-depth diagnostic view of a session's behavioral state and metadata."""
    s = await run_in_threadpool(load_session, session_id=session_id)
    return {
        "sessionId": s.sessionId,
        "behaviorState": s.bf_state,
        "lastIntent": s.bf_last_intent,
        "trajectoryLength": len(s.trajectory),
        "hybridMetadata": s.hybridMetadata,
        "lastRedFlag": s.lastRedFlagTag,
        "personaStyle": s.lastPersonaStyle,
        "turnsEngaged": s.turnsEngaged,
        "state": s.state,
    }

@router.get("/debug/hybrid/feature-flags")
def debug_hybrid_feature_flags(_=Depends(require_api_key)):
    """Diagnostic view of hybrid-specific flags."""
    return {
        "EXTERNAL_REPORTING_MODE": settings.EXTERNAL_REPORTING_MODE,
        "FINAL_OUTPUT_MODE": settings.FINAL_OUTPUT_MODE,
        "FINAL_OUTPUT_DEADLINE_SEC": settings.FINAL_OUTPUT_DEADLINE_SEC,
    }

@router.get("/debug/intent-map")
def debug_intent_map(_=Depends(require_api_key)):
    return {"keys": snapshot_intent_map()}

@router.post("/debug/intent-map/reload")
def debug_intent_map_reload(_=Depends(require_api_key)):
    keys, ts = reload_intent_map()
    return {"reloadedKeys": keys, "reloadedAtEpoch": ts}

@router.get("/debug/last-callback/{session_id}")
def debug_last_callback_payload(session_id: str, _=Depends(require_api_key)):
    if not settings.STORE_LAST_CALLBACK_PAYLOAD:
        return {"enabled": False}
    try:
        r = get_redis()
        raw = r.get(f"session:{session_id}:last_callback_payload")
        return {"sessionId": session_id, "payload": (raw and json.loads(raw)) or None}
    except Exception:
        return {"sessionId": session_id, "payload": None}
