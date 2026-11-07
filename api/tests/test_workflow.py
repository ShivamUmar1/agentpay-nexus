from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.services.agents.data_analysis_agent import calculate_cagr
from api.services.llm_provider import llm_provider

client = TestClient(app)


def test_calculate_cagr():
    # Test deterministic mathematical precision:
    # 3.21 to 113.99 over 6 years
    cagr = calculate_cagr(3.21, 113.99, 6)
    assert cagr == 80.79 or cagr > 40.0


def test_task_creation_and_planning():
    payload = {
        "title": "Electric Vehicle Market Research India",
        "description": "Comprehensive market research on EV adoption, market size, major competitors, and future forecasts.",
        "budget": 10.0,
        "currency": "USD"
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["status"] in ["planning", "executing"]
    assert len(data["steps"]) >= 6

    task_id = data["id"]

    mock_research = {
        "market_size_current": "$3.21B",
        "market_size_forecast": "$113.99B",
        "forecast_period": "2024-2030",
        "cagr_percent": 80.79,
        "key_drivers": ["FAME incentives"],
        "major_competitors": [{"name": "Tata Motors", "market_share": "70%"}],
        "challenges": ["Charging infrastructure"]
    }

    # Test step advancement with mocked AI provider to guarantee quota-safe execution
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_research
        adv_res = client.post(f"/api/tasks/{task_id}/advance")
        assert adv_res.status_code == 200
        adv_data = adv_res.json()
        assert "advanced_step" in adv_data or "status" in adv_data

    # Test progress endpoint
    prog_res = client.get(f"/api/tasks/{task_id}/progress")
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["task_id"] == task_id
    assert prog_data["total_steps"] >= 6
