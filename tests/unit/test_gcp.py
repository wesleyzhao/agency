"""Tests for GCP utilities."""
import pytest
from unittest.mock import patch, Mock, MagicMock

from agentctl.shared.gcp import get_project_id, verify_auth, GCPError


def test_get_project_id_from_service_account():
    """Test getting project ID from service account file."""
    mock_credentials = MagicMock()

    with patch("agentctl.shared.gcp.get_credentials") as mock_get_creds:
        mock_get_creds.return_value = (mock_credentials, "test-project")

        result = get_project_id("/fake/path/sa.json")
        assert result == "test-project"
        mock_get_creds.assert_called_once_with("/fake/path/sa.json")


def test_get_project_id_no_credentials():
    """Test get_project_id returns None when no credentials."""
    with patch("agentctl.shared.gcp.get_credentials") as mock_get_creds:
        mock_get_creds.side_effect = GCPError("No credentials")

        result = get_project_id()
        assert result is None


def test_verify_auth_success():
    """Test verify_auth returns True with valid credentials."""
    mock_credentials = MagicMock()
    # Mock the refresh method to succeed
    mock_credentials.refresh = MagicMock()

    with patch("agentctl.shared.gcp.get_credentials") as mock_get_creds:
        mock_get_creds.return_value = (mock_credentials, "test-project")

        with patch("google.auth.transport.requests.Request"):
            result = verify_auth("/fake/path/sa.json")
            assert result is True


def test_verify_auth_no_credentials():
    """Test verify_auth returns False when no credentials."""
    with patch("agentctl.shared.gcp.get_credentials") as mock_get_creds:
        mock_get_creds.side_effect = GCPError("No credentials")

        result = verify_auth()
        assert result is False


def test_gcp_error_class():
    """Test GCPError exception."""
    from agentctl.shared.gcp import GCPError

    error = GCPError("Something failed")
    assert str(error) == "Something failed"
