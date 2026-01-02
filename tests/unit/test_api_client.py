"""Tests for API client module."""
import pytest
import httpx
from unittest.mock import Mock, patch
from agentctl.shared.api_client import APIClient, APIError
from agentctl.shared.models import AgentConfig, EngineType


def test_api_client_health_check_success():
    """Health check should return True when server is healthy."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "healthy"}'
        mock_response.json.return_value = {"status": "healthy"}
        mock_client.return_value.request.return_value = mock_response

        client = APIClient("http://localhost:8080")
        assert client.health_check() is True


def test_api_client_health_check_failure():
    """Health check should return False when server is down."""
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.request.side_effect = httpx.ConnectError("Connection refused")

        client = APIClient("http://localhost:8080")
        assert client.health_check() is False


def test_api_client_create_agent():
    """Create agent should POST to /agents."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "test-123"}'
        mock_response.json.return_value = {"id": "test-123"}
        mock_client.return_value.request.return_value = mock_response

        client = APIClient("http://localhost:8080")
        config = AgentConfig(prompt="Test prompt")
        result = client.create_agent(config)

        assert result["id"] == "test-123"
        mock_client.return_value.request.assert_called_once()
        call_args = mock_client.return_value.request.call_args
        assert call_args[0][0] == "POST"
        assert "/agents" in call_args[0][1]


def test_api_client_error_handling():
    """API errors should raise APIError."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'{"detail": "Not found"}'
        mock_response.json.return_value = {"detail": "Not found"}
        mock_response.text = "Not found"
        mock_client.return_value.request.return_value = mock_response

        client = APIClient("http://localhost:8080")
        with pytest.raises(APIError) as exc:
            client.get_agent("nonexistent")
        assert exc.value.status_code == 404
