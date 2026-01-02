"""Tests for GCP utilities."""
import pytest
from unittest.mock import patch, Mock
from agentctl.shared.gcp import get_project_id, verify_auth


def test_get_project_id_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="my-project\n", returncode=0)
        assert get_project_id() == "my-project"


def test_get_project_id_empty():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="\n", returncode=0)
        assert get_project_id() is None


def test_verify_auth_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="user@example.com\n", returncode=0)
        assert verify_auth() is True


def test_verify_auth_not_authenticated():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="", returncode=0)
        assert verify_auth() is False
