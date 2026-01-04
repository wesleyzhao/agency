"""Tests for launcher.py - TDD style.

These tests define the expected behavior of the launcher module.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestLauncherInit:
    """Tests for QuickDeployLauncher initialization."""

    def test_init_with_config(self):
        """Should initialize with config."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        assert launcher.config == config


class TestLaunchAgent:
    """Tests for launching an agent."""

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    @patch("agency_quickdeploy.launcher.SecretManager")
    def test_launch_returns_result(
        self, mock_secret_class, mock_storage_class, mock_vm_class
    ):
        """Launch should return a LaunchResult."""
        from agency_quickdeploy.launcher import QuickDeployLauncher, LaunchResult
        from agency_quickdeploy.config import QuickDeployConfig

        # Setup mocks
        mock_secret = MagicMock()
        mock_secret.get.return_value = "test-api-key"
        mock_secret_class.return_value = mock_secret

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "agent-123", "status": "creating"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        result = launcher.launch("Build a todo app")

        assert isinstance(result, LaunchResult)
        assert result.agent_id is not None
        assert result.status in ["launching", "running", "creating"]

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    @patch("agency_quickdeploy.launcher.SecretManager")
    def test_launch_generates_agent_id(
        self, mock_secret_class, mock_storage_class, mock_vm_class
    ):
        """Launch should generate a unique agent ID."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_secret = MagicMock()
        mock_secret.get.return_value = "test-api-key"
        mock_secret_class.return_value = mock_secret

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "test", "status": "creating"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        result1 = launcher.launch("Build app 1")
        result2 = launcher.launch("Build app 2")

        assert result1.agent_id != result2.agent_id

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    @patch("agency_quickdeploy.launcher.SecretManager")
    def test_launch_ensures_bucket_exists(
        self, mock_secret_class, mock_storage_class, mock_vm_class
    ):
        """Launch should ensure GCS bucket exists."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_secret = MagicMock()
        mock_secret.get.return_value = "test-api-key"
        mock_secret_class.return_value = mock_secret

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "test", "status": "creating"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        launcher.launch("Build an app")

        mock_storage.ensure_bucket.assert_called_once()


class TestAgentStatus:
    """Tests for getting agent status."""

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    def test_status_returns_dict(self, mock_storage_class, mock_vm_class):
        """Status should return agent status dict."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_storage = MagicMock()
        mock_storage.get_agent_status.return_value = {
            "agent_id": "agent-123",
            "status": "running",
            "feature_count": 5,
        }
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.get.return_value = {"status": "RUNNING", "external_ip": "1.2.3.4"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        status = launcher.status("agent-123")

        assert status["status"] == "running"
        mock_storage.get_agent_status.assert_called_with("agent-123")


class TestStopAgent:
    """Tests for stopping an agent."""

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    def test_stop_deletes_vm(self, mock_storage_class, mock_vm_class):
        """Stop should delete the VM."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.delete.return_value = True
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        result = launcher.stop("agent-123")

        assert result is True
        mock_vm.delete.assert_called_with("agent-123")


class TestListAgents:
    """Tests for listing agents."""

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    def test_list_returns_agents(self, mock_storage_class, mock_vm_class):
        """List should return agent info from VMs."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.list_by_label.return_value = [
            {"name": "agent-001", "status": "RUNNING"},
            {"name": "agent-002", "status": "TERMINATED"},
        ]
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        agents = launcher.list_agents()

        assert len(agents) == 2


class TestEnvVarApiKey:
    """Tests for environment variable API key support."""

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    @patch("agency_quickdeploy.launcher.SecretManager")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-from-env"})
    def test_uses_env_var_api_key_when_set(
        self, mock_secret_class, mock_storage_class, mock_vm_class
    ):
        """Should use ANTHROPIC_API_KEY env var when set, skipping Secret Manager."""
        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "test", "status": "creating"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        result = launcher.launch("Build an app")

        # Should NOT call Secret Manager since env var is set
        mock_secret_class.return_value.get.assert_not_called()
        # Should still create VM successfully
        assert result.status in ["launching", "running", "creating"]

    @patch("agency_quickdeploy.launcher.VMManager")
    @patch("agency_quickdeploy.launcher.QuickDeployStorage")
    @patch("agency_quickdeploy.launcher.SecretManager")
    @patch.dict("os.environ", {}, clear=True)
    def test_falls_back_to_secret_manager_when_no_env_var(
        self, mock_secret_class, mock_storage_class, mock_vm_class
    ):
        """Should fall back to Secret Manager when ANTHROPIC_API_KEY not set."""
        import os
        # Ensure env var is not set
        os.environ.pop("ANTHROPIC_API_KEY", None)

        from agency_quickdeploy.launcher import QuickDeployLauncher
        from agency_quickdeploy.config import QuickDeployConfig

        mock_secret = MagicMock()
        mock_secret.get.return_value = "test-api-key-from-secret"
        mock_secret_class.return_value = mock_secret

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "test", "status": "creating"}
        mock_vm_class.return_value = mock_vm

        config = QuickDeployConfig(gcp_project="test-project")
        launcher = QuickDeployLauncher(config)

        result = launcher.launch("Build an app")

        # Should call Secret Manager since env var is not set
        mock_secret.get.assert_called_once()
        assert result.status in ["launching", "running", "creating"]
