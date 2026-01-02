"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from agentctl.server import database
from agentctl.server.app import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use temporary database."""
    database.DB_PATH = tmp_path / "test.db"
    database.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_get_agent(client):
    """Full create/get cycle."""
    # Create
    response = client.post("/agents", json={
        "prompt": "Build something",
        "engine": "claude"
    })
    assert response.status_code == 201
    data = response.json()
    agent_id = data["id"]

    # Get
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["prompt"] == "Build something"


def test_list_agents(client):
    """List should return created agents."""
    client.post("/agents", json={"prompt": "Test 1"})
    client.post("/agents", json={"prompt": "Test 2"})

    response = client.get("/agents")
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_stop_agent(client):
    """Stop should change status."""
    # Create
    response = client.post("/agents", json={"prompt": "Test"})
    agent_id = response.json()["id"]

    # Update to running (simulate VM started)
    from agentctl.server import repository
    from agentctl.shared.models import AgentStatus
    repository.update_agent_status(agent_id, AgentStatus.RUNNING)

    # Stop
    response = client.post(f"/agents/{agent_id}/stop")
    assert response.status_code == 200

    # Verify stopped
    response = client.get(f"/agents/{agent_id}")
    assert response.json()["status"] == "stopped"


def test_delete_agent(client):
    """Delete should remove agent."""
    response = client.post("/agents", json={"prompt": "Test"})
    agent_id = response.json()["id"]

    response = client.delete(f"/agents/{agent_id}")
    assert response.status_code == 204

    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 404


def test_agent_not_found(client):
    """Should return 404 for nonexistent agent."""
    response = client.get("/agents/nonexistent")
    assert response.status_code == 404
