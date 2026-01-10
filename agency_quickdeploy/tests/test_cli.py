"""Tests for CLI commands (TDD - Phase 1.3).

These tests verify CLI behavior, particularly the enhanced init command
for Railway that validates tokens and tests API connectivity.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock


class TestInitCommandRailway:
    """Tests for init command with Railway provider."""

    @patch("agency_quickdeploy.cli.load_config")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_format")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_api")
    def test_init_validates_token_format(
        self, mock_validate_api, mock_validate_format, mock_load_config
    ):
        """init --provider railway should validate token format."""
        from agency_quickdeploy.cli import cli
        from agency_quickdeploy.providers.base import ProviderType

        mock_config = MagicMock()
        mock_config.provider = ProviderType.RAILWAY
        mock_config.railway_token = "3fca9fef-8953-486f-b772-af5f34417ef7"
        mock_config.railway_project_id = None
        mock_load_config.return_value = mock_config
        mock_validate_format.return_value = True
        mock_validate_api.return_value = (True, None)

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--provider", "railway"])

        # Should validate format
        mock_validate_format.assert_called_once_with(mock_config.railway_token)
        assert result.exit_code == 0

    @patch("agency_quickdeploy.cli.load_config")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_format")
    def test_init_shows_error_for_invalid_token_format(
        self, mock_validate_format, mock_load_config
    ):
        """init should show error for invalid token format."""
        from agency_quickdeploy.cli import cli
        from agency_quickdeploy.providers.base import ProviderType

        mock_config = MagicMock()
        mock_config.provider = ProviderType.RAILWAY
        mock_config.railway_token = "invalid-token"
        mock_config.railway_project_id = None
        mock_load_config.return_value = mock_config
        mock_validate_format.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--provider", "railway"])

        # Should show error about token format
        assert "format" in result.output.lower() or "invalid" in result.output.lower()

    @patch("agency_quickdeploy.cli.load_config")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_format")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_api")
    def test_init_tests_api_connectivity(
        self, mock_validate_api, mock_validate_format, mock_load_config
    ):
        """init should test API connectivity after format validation."""
        from agency_quickdeploy.cli import cli
        from agency_quickdeploy.providers.base import ProviderType

        mock_config = MagicMock()
        mock_config.provider = ProviderType.RAILWAY
        mock_config.railway_token = "valid-token-format"
        mock_config.railway_project_id = "proj-123"
        mock_load_config.return_value = mock_config
        mock_validate_format.return_value = True
        mock_validate_api.return_value = (True, None)

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--provider", "railway"])

        # Should test API connectivity
        mock_validate_api.assert_called_once_with(mock_config.railway_token)
        assert result.exit_code == 0
        # Should show success message
        assert "connected" in result.output.lower() or "valid" in result.output.lower()

    @patch("agency_quickdeploy.cli.load_config")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_format")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_api")
    def test_init_shows_api_error(
        self, mock_validate_api, mock_validate_format, mock_load_config
    ):
        """init should show actionable error when API check fails."""
        from agency_quickdeploy.cli import cli
        from agency_quickdeploy.providers.base import ProviderType

        mock_config = MagicMock()
        mock_config.provider = ProviderType.RAILWAY
        mock_config.railway_token = "valid-format-but-bad-token"
        mock_config.railway_project_id = None
        mock_load_config.return_value = mock_config
        mock_validate_format.return_value = True
        mock_validate_api.return_value = (False, "Token expired. Get new token at railway.com/account/tokens")

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--provider", "railway"])

        # Should show the API error message
        assert "railway.com" in result.output or "token" in result.output.lower()

    @patch("agency_quickdeploy.cli.load_config")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_format")
    @patch("agency_quickdeploy.providers.railway.validate_railway_token_api")
    def test_init_shows_project_info_when_connected(
        self, mock_validate_api, mock_validate_format, mock_load_config
    ):
        """init should show project info when successfully connected."""
        from agency_quickdeploy.cli import cli
        from agency_quickdeploy.providers.base import ProviderType

        mock_config = MagicMock()
        mock_config.provider = ProviderType.RAILWAY
        mock_config.railway_token = "valid-token"
        mock_config.railway_project_id = "proj-abc123"
        mock_load_config.return_value = mock_config
        mock_validate_format.return_value = True
        mock_validate_api.return_value = (True, None)

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--provider", "railway"])

        assert result.exit_code == 0
        # Should show project ID
        assert "proj-abc123" in result.output or "project" in result.output.lower()
