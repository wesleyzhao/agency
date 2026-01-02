"""Tests for agent management commands."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_list_empty():
    """List should handle empty results."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.list_agents.return_value = []
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "No agents found" in result.output


def test_list_with_agents():
    """List should display agents."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.list_agents.return_value = [
            {"id": "agent-1", "status": "running", "engine": "claude", "created_at": "2025-01-01T00:00:00"}
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "agent-1" in result.output


def test_status_command():
    """Status should show agent details."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.get_agent.return_value = {
            "id": "agent-1",
            "status": "running",
            "engine": "claude",
            "prompt": "Test prompt",
            "created_at": "2025-01-01T00:00:00"
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["status", "agent-1"])

        assert result.exit_code == 0
        assert "agent-1" in result.output
        assert "running" in result.output


def test_stop_with_confirmation():
    """Stop should require confirmation."""
    runner = CliRunner()
    result = runner.invoke(cli, ["stop", "agent-1"], input="n\n")
    assert result.exit_code == 0
    # Should not have called API


def test_stop_with_force():
    """Stop with --force should skip confirmation."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.stop_agent.return_value = {}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["stop", "--force", "agent-1"])

        assert result.exit_code == 0
        mock_client.stop_agent.assert_called_once_with("agent-1")
