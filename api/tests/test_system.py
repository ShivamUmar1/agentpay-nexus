import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "ai_orchestration" in data
    assert "payment_gateway" in data
    assert "database" in data
    assert data["database"]["status"] in ["connected", "error"]
    assert "status" in data["ai_orchestration"]
    assert "status" in data["payment_gateway"]
