from fastapi.testclient import TestClient
from ops.main import app

client = TestClient(app)

def test_ops_health():
    response = client.get("/api/ops/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
