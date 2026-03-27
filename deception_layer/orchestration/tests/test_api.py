import pytest
from fastapi.testclient import TestClient
from orchestration.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/orchestration/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "orchestration"}

def test_evaluate_trigger_banned():
    # Test local policy enforcement (banned actor)
    payload = {
        "session_id": "test-session",
        "trigger_type": "banned_actor",
        "payload": {}
    }
    response = client.post("/api/orchestration/evaluate", json=payload)
    assert response.status_code == 403
    assert "Policy violation" in response.json()["detail"]
