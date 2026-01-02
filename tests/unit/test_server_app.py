"""Tests for server app."""
import pytest
from fastapi.testclient import TestClient
from agentctl.server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Health endpoint should return healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
