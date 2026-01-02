"""Tests for run command."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_run_requires_prompt():
    """Run should fail without prompt."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Prompt is required" in result.output


def test_run_with_prompt():
    """Run should create agent with prompt."""
    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-agent-123"}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "Build a todo app"])

        assert result.exit_code == 0
        assert "test-agent-123" in result.output
        mock_client.create_agent.assert_called_once()


def test_run_with_options():
    """Run should pass options to API."""
    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-123"}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, [
            "run",
            "--name", "my-agent",
            "--engine", "claude",
            "--timeout", "2h",
            "--spot",
            "Build something"
        ])

        assert result.exit_code == 0
        call_args = mock_client.create_agent.call_args[0][0]
        assert call_args.name == "my-agent"
        assert call_args.timeout_seconds == 7200
        assert call_args.spot is True


def test_run_with_prompt_file(tmp_path):
    """Run should read prompt from file."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Build from file")

    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-123"}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--prompt-file", str(prompt_file)])

        assert result.exit_code == 0
        call_args = mock_client.create_agent.call_args[0][0]
        assert call_args.prompt == "Build from file"
