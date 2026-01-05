"""Tests for the GCP provider wrapper.

TDD: Tests written first, before implementation.
"""

import pytest
from unittest.mock import MagicMock, patch

from agency_quickdeploy.providers import BaseProvider, DeploymentResult
from agency_quickdeploy.providers.gcp import GCPProvider
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import Credentials, AuthType


class TestGCPProviderInit:
    """Tests for GCPProvider initialization."""

    def test_gcp_provider_is_base_provider(self):
        """GCPProvider should implement BaseProvider."""
        assert issubclass(GCPProvider, BaseProvider)

    def test_gcp_provider_requires_config(self):
        """GCPProvider should require a QuickDeployConfig."""
        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)
        assert provider.config == config

    def test_gcp_provider_lazy_init_vm_manager(self):
        """GCPProvider should lazy-initialize VM manager."""
        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)
        # Should not be initialized yet
        assert provider._vm_manager is None


class TestGCPProviderLaunch:
    """Tests for GCPProvider.launch()."""

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    @patch("agency_quickdeploy.providers.gcp.generate_startup_script")
    def test_launch_returns_deployment_result(
        self, mock_startup, mock_storage_class, mock_vm_class
    ):
        """launch() should return a DeploymentResult."""
        # Setup mocks
        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "agent-123"}
        mock_vm_class.return_value = mock_vm

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_startup.return_value = "#!/bin/bash\necho hello"

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        credentials = Credentials.from_api_key("sk-ant-test")
        result = provider.launch(
            agent_id="agent-123",
            prompt="Build an app",
            credentials=credentials,
        )

        assert isinstance(result, DeploymentResult)
        assert result.agent_id == "agent-123"
        assert result.provider == "gcp"
        assert result.status == "launching"

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    @patch("agency_quickdeploy.providers.gcp.generate_startup_script")
    def test_launch_creates_vm(
        self, mock_startup, mock_storage_class, mock_vm_class
    ):
        """launch() should create a VM with correct parameters."""
        mock_vm = MagicMock()
        mock_vm.create.return_value = {"name": "agent-123"}
        mock_vm_class.return_value = mock_vm

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_startup.return_value = "#!/bin/bash\necho hello"

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        credentials = Credentials.from_api_key("sk-ant-test")
        provider.launch(
            agent_id="agent-123",
            prompt="Build an app",
            credentials=credentials,
        )

        # Verify VM creation was called
        mock_vm.create.assert_called_once()
        call_kwargs = mock_vm.create.call_args[1]
        assert call_kwargs["name"] == "agent-123"

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    @patch("agency_quickdeploy.providers.gcp.generate_startup_script")
    def test_launch_handles_error(
        self, mock_startup, mock_storage_class, mock_vm_class
    ):
        """launch() should handle errors gracefully."""
        mock_vm = MagicMock()
        mock_vm.create.side_effect = Exception("VM creation failed")
        mock_vm_class.return_value = mock_vm

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        mock_startup.return_value = "#!/bin/bash\necho hello"

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        credentials = Credentials.from_api_key("sk-ant-test")
        result = provider.launch(
            agent_id="agent-123",
            prompt="Build an app",
            credentials=credentials,
        )

        assert result.status == "failed"
        assert "VM creation failed" in result.error


class TestGCPProviderStatus:
    """Tests for GCPProvider.status()."""

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    def test_status_returns_dict(self, mock_storage_class, mock_vm_class):
        """status() should return a dict with agent info."""
        mock_vm = MagicMock()
        mock_vm.get.return_value = {"status": "RUNNING", "external_ip": "1.2.3.4"}
        mock_vm_class.return_value = mock_vm

        mock_storage = MagicMock()
        mock_storage.get_agent_status.return_value = {"status": "running"}
        mock_storage_class.return_value = mock_storage

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        result = provider.status("agent-123")

        assert isinstance(result, dict)
        assert result.get("vm_status") == "RUNNING"


class TestGCPProviderLogs:
    """Tests for GCPProvider.logs()."""

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    def test_logs_returns_content(self, mock_storage_class, mock_vm_class):
        """logs() should return log content from GCS."""
        mock_vm_class.return_value = MagicMock()

        mock_storage = MagicMock()
        mock_storage.download.return_value = "Some log content"
        mock_storage_class.return_value = mock_storage

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        result = provider.logs("agent-123")

        assert result == "Some log content"
        mock_storage.download.assert_called_with("agents/agent-123/logs/agent.log")


class TestGCPProviderStop:
    """Tests for GCPProvider.stop()."""

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    def test_stop_deletes_vm(self, mock_storage_class, mock_vm_class):
        """stop() should delete the VM."""
        mock_vm = MagicMock()
        mock_vm.delete.return_value = True
        mock_vm_class.return_value = mock_vm

        mock_storage_class.return_value = MagicMock()

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        result = provider.stop("agent-123")

        assert result is True
        mock_vm.delete.assert_called_with("agent-123")


class TestGCPProviderListAgents:
    """Tests for GCPProvider.list_agents()."""

    @patch("agency_quickdeploy.providers.gcp.VMManager")
    @patch("agency_quickdeploy.providers.gcp.QuickDeployStorage")
    def test_list_agents_returns_list(self, mock_storage_class, mock_vm_class):
        """list_agents() should return list of agents."""
        mock_vm = MagicMock()
        mock_vm.list_by_label.return_value = [
            {"name": "agent-1", "status": "RUNNING"},
            {"name": "agent-2", "status": "TERMINATED"},
        ]
        mock_vm_class.return_value = mock_vm

        mock_storage_class.return_value = MagicMock()

        config = QuickDeployConfig(gcp_project="test-project")
        provider = GCPProvider(config)

        result = provider.list_agents()

        assert isinstance(result, list)
        assert len(result) == 2
        mock_vm.list_by_label.assert_called_with("agency-quickdeploy", "true")
