"""Tests for GCP utilities."""
import pytest
from unittest.mock import patch, Mock, MagicMock


def test_get_project_id_from_service_account(tmp_path):
    """Test getting project ID from service account file."""
    import json

    # Create a mock service account file
    sa_file = tmp_path / "sa.json"
    sa_data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...fake...key\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
    }
    sa_file.write_text(json.dumps(sa_data))

    with patch("agentctl.shared.gcp.service_account.Credentials") as mock_creds:
        mock_creds.from_service_account_file.return_value = MagicMock()

        from agentctl.shared.gcp import get_project_id
        result = get_project_id(str(sa_file))
        assert result == "test-project"


def test_get_project_id_no_credentials():
    """Test get_project_id returns None when no credentials."""
    with patch("agentctl.shared.gcp.google.auth.default") as mock_default:
        from google.auth import exceptions
        mock_default.side_effect = exceptions.DefaultCredentialsError("No creds")

        from agentctl.shared.gcp import get_project_id
        result = get_project_id()
        assert result is None


def test_verify_auth_success(tmp_path):
    """Test verify_auth returns True with valid credentials."""
    import json

    sa_file = tmp_path / "sa.json"
    sa_data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...fake...key\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
    }
    sa_file.write_text(json.dumps(sa_data))

    with patch("agentctl.shared.gcp.service_account.Credentials") as mock_creds:
        mock_cred_instance = MagicMock()
        mock_creds.from_service_account_file.return_value = mock_cred_instance

        from agentctl.shared.gcp import verify_auth
        result = verify_auth(str(sa_file))
        assert result is True


def test_verify_auth_no_credentials():
    """Test verify_auth returns False when no credentials."""
    with patch("agentctl.shared.gcp.google.auth.default") as mock_default:
        from google.auth import exceptions
        mock_default.side_effect = exceptions.DefaultCredentialsError("No creds")

        from agentctl.shared.gcp import verify_auth
        result = verify_auth()
        assert result is False


def test_gcp_error_class():
    """Test GCPError exception."""
    from agentctl.shared.gcp import GCPError

    error = GCPError("Something failed")
    assert str(error) == "Something failed"
