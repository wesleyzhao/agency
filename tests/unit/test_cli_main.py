"""Tests for CLI main module."""
from click.testing import CliRunner
from agentctl.cli.main import cli


def test_cli_help():
    """CLI should show help text."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "AgentCtl" in result.output


def test_cli_version():
    """CLI should show version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
