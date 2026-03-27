from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict, Any
import logging
import json

app = FastAPI(title="Deception Layer Ops Surface")
logger = logging.getLogger("ops")

class ConnectionManager:
    """Manages real-time connections to the Ops surface"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

def check_admin_auth(token: str = "placeholder"):
    # Admin Auth/Authz placeholder - Role Based (e.g. JWT with 'admin' scope)
    return token == "admin-secret"

@app.get("/api/ops/health")
def health():
    """External layer health and dependency status"""
    return {"status": "ok", "active_connections": len(manager.active_connections)}

@app.get("/api/ops/session/{session_id}")
async def get_live_session(session_id: str, is_admin: bool = Depends(check_admin_auth)):
    """Live session/trajectory lookup"""
    # In real implementation, this forwards to the Python brain or a shared data store (Redis)
    return {"session_id": session_id, "status": "active", "trajectory": []}

@app.websocket("/ws/ops/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time telemetry updates and live session views"""
    await manager.connect(websocket)
    try:
        while True:
            # Ops clients can send commands or filters
            data = await websocket.receive_text()
            logger.info(f"Received from ops client: {data}")
            
            # Simple echo/ack
            await websocket.send_text(json.dumps({"event": "ack", "data": data}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Ops client disconnected")

@app.post("/api/ops/internal/ingest_event")
async def ingest_brain_event(event_payload: Dict[str, Any]):
    """
    Webhook/Event intake for Python Brain to push live session trajectories 
    to the Ops layer. Treats Python as the source of truth for behavior state.
    """
    await manager.broadcast(json.dumps({
        "type": "trajectory_update",
        "payload": event_payload
    }))
    return {"status": "broadcasted"}
