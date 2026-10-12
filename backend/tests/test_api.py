from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_validation_rejects_unknown_model():
    with TestClient(app) as client:
        response = client.post("/api/runs", json={"name": "bad", "models": ["not-real"]})
    assert response.status_code == 422
    assert "unknown model" in response.json()["detail"]

