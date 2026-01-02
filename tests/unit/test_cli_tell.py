"""Tests for tell command."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_tell_requires_instruction():
    """Tell should fail without instruction."""
    runner = CliRunner()
    result = runner.invoke(cli, ["tell", "agent-1"])
    assert result.exit_code != 0
    assert "Instruction required" in result.output


def test_tell_with_instruction():
    """Tell should send instruction."""
    with patch("agentctl.cli.tell.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.tell_agent.return_value = {}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["tell", "agent-1", "Add tests"])

        assert result.exit_code == 0
        mock_client.tell_agent.assert_called_once_with("agent-1", "Add tests")
