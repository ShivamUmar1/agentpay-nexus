import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_list_agents():
    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert data["total"] >= 6
    agent_ids = [a["id"] for a in data["agents"]]
    assert "agent_research_01" in agent_ids
    assert "agent_analysis_02" in agent_ids
    assert "agent_content_03" in agent_ids
    assert "agent_qa_04" in agent_ids


def test_filter_agents_by_category():
    response = client.get("/api/agents?category=Research")
    assert response.status_code == 200
    data = response.json()
    for agent in data["agents"]:
        assert agent["category"] == "Research"


def test_get_single_agent():
    response = client.get("/api/agents/agent_research_01")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Deep Research Agent"
    assert data["price"] == 2.0
    assert isinstance(data["capabilities"], list)
