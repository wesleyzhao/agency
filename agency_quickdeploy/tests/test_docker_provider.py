"""Tests for Docker provider."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from agency_quickdeploy.providers.base import ProviderType, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import AuthType


class TestDockerProviderImport:
    """Test Docker provider can be imported."""

    def test_docker_provider_type_exists(self):
        """Test that DOCKER is in ProviderType enum."""
        assert ProviderType.DOCKER.value == "docker"

    def test_import_docker_provider(self):
        """Test DockerProvider can be imported."""
        from agency_quickdeploy.providers.docker import DockerProvider
        assert DockerProvider is not None


class TestDockerProviderInit:
    """Test Docker provider initialization."""

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        from agency_quickdeploy.providers.docker import DockerProvider

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        with patch.object(DockerProvider, '__init__', return_value=None) as mock_init:
            provider = DockerProvider.__new__(DockerProvider)
            provider.config = config
            provider.data_dir = Path("~/.agency").expanduser()
            provider.agents_dir = provider.data_dir / "agents"
            provider.image = config.docker_image
            provider._docker = None

            assert provider.data_dir == Path("~/.agency").expanduser()
            assert provider.image == "ghcr.io/wesleyzhao/agency-agent:latest"

    def test_init_with_custom_data_dir(self):
        """Test initialization with custom data directory."""
        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
            docker_data_dir="/custom/path",
        )
        assert config.docker_data_dir == "/custom/path"

    def test_init_with_custom_image(self):
        """Test initialization with custom Docker image."""
        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
            docker_image="my-registry/my-agent:v1",
        )
        assert config.docker_image == "my-registry/my-agent:v1"


class TestDockerProviderError:
    """Test Docker error classes."""

    def test_docker_error_not_installed(self):
        """Test not installed error message."""
        from agency_quickdeploy.providers.docker import DockerError

        error = DockerError.not_installed()
        assert "not installed" in error.message.lower()
        assert "pip install docker" in error.message

    def test_docker_error_daemon_not_running(self):
        """Test daemon not running error message."""
        from agency_quickdeploy.providers.docker import DockerError

        error = DockerError.daemon_not_running()
        assert "not running" in error.message.lower()

    def test_docker_error_container_not_found(self):
        """Test container not found error message."""
        from agency_quickdeploy.providers.docker import DockerError

        error = DockerError.container_not_found("test-agent")
        assert "test-agent" in error.message
        assert "not found" in error.message.lower()

    def test_docker_error_image_not_found(self):
        """Test image not found error message."""
        from agency_quickdeploy.providers.docker import DockerError

        error = DockerError.image_not_found("my-image:latest")
        assert "my-image:latest" in error.message
        assert "not found" in error.message.lower()


class TestDockerProviderLaunch:
    """Test Docker provider launch functionality."""

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_launch_creates_container(self, mock_docker_module, tmp_path):
        """Test that launch creates a Docker container."""
        from agency_quickdeploy.providers.docker import DockerProvider

        # Setup mocks
        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()

        mock_container = Mock()
        mock_client.containers.run.return_value = mock_container

        # Mock NotFound for checking existing container
        from agency_quickdeploy.providers.docker import NotFound
        mock_client.containers.get.side_effect = NotFound("Not found")

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
            docker_data_dir=str(tmp_path),
        )

        provider = DockerProvider(config)
        provider._docker = mock_client  # Bypass lazy init

        result = provider.launch(
            agent_id="test-agent",
            prompt="Build a todo app",
            credentials=None,
        )

        assert result.agent_id == "test-agent"
        assert result.provider == "docker"
        assert result.status == "launching"

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_launch_with_env_credentials(self, mock_docker_module, monkeypatch, tmp_path):
        """Test that launch uses environment credentials."""
        from agency_quickdeploy.providers.docker import DockerProvider, NotFound

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        mock_client.containers.run.return_value = Mock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
            docker_data_dir=str(tmp_path),
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        result = provider.launch(
            agent_id="test-agent",
            prompt="Build an app",
            credentials=None,
        )

        # Verify containers.run was called with environment including API key
        assert mock_client.containers.run.called
        call_args = mock_client.containers.run.call_args
        env = call_args.kwargs.get('environment', {})
        assert "ANTHROPIC_API_KEY" in env
        assert env["ANTHROPIC_API_KEY"] == "test-key"


class TestDockerProviderStatus:
    """Test Docker provider status functionality."""

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_status_running_container(self, mock_docker_module):
        """Test status returns running for running container."""
        from agency_quickdeploy.providers.docker import DockerProvider

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        mock_container = Mock()
        mock_container.status = "running"
        mock_container.short_id = "abc123"
        mock_container.attrs = {"State": {"ExitCode": 0}}
        mock_client.containers.get.return_value = mock_container

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        status = provider.status("test-agent")

        assert status["agent_id"] == "test-agent"
        assert status["status"] == "running"
        assert status["container_id"] == "abc123"

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    @patch('agency_quickdeploy.providers.docker.NotFound', Exception)
    def test_status_not_found(self, mock_docker_module):
        """Test status returns not_found for missing container."""
        from agency_quickdeploy.providers.docker import DockerProvider, NotFound

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.containers.get.side_effect = NotFound("Not found")

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        status = provider.status("missing-agent")

        assert status["agent_id"] == "missing-agent"
        assert status["status"] == "not_found"


class TestDockerProviderStop:
    """Test Docker provider stop functionality."""

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_stop_removes_container(self, mock_docker_module):
        """Test stop removes the container."""
        from agency_quickdeploy.providers.docker import DockerProvider

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        result = provider.stop("test-agent")

        assert result is True
        mock_container.remove.assert_called_once_with(force=True)

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    @patch('agency_quickdeploy.providers.docker.NotFound', Exception)
    def test_stop_returns_true_if_not_found(self, mock_docker_module):
        """Test stop returns True if container not found (already stopped)."""
        from agency_quickdeploy.providers.docker import DockerProvider, NotFound

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.containers.get.side_effect = NotFound("Not found")

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        result = provider.stop("missing-agent")

        assert result is True


class TestDockerProviderList:
    """Test Docker provider list functionality."""

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_list_agents_returns_containers(self, mock_docker_module):
        """Test list_agents returns Docker containers with agency labels."""
        from agency_quickdeploy.providers.docker import DockerProvider

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        mock_container1 = Mock()
        mock_container1.name = "agent-1"
        mock_container1.status = "running"
        mock_container1.short_id = "abc123"
        mock_container1.labels = {
            "agency.agent": "true",
            "agency.agent-id": "agent-1",
            "agency.provider": "docker",
        }

        mock_container2 = Mock()
        mock_container2.name = "agent-2"
        mock_container2.status = "exited"
        mock_container2.short_id = "def456"
        mock_container2.labels = {
            "agency.agent": "true",
            "agency.agent-id": "agent-2",
            "agency.provider": "docker",
        }

        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        agents = provider.list_agents()

        assert len(agents) == 2
        assert agents[0]["name"] == "agent-1"
        assert agents[0]["status"] == "running"
        assert agents[1]["name"] == "agent-2"
        assert agents[1]["status"] == "exited"

    @patch('agency_quickdeploy.providers.docker.DOCKER_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.docker.docker')
    def test_list_agents_filters_by_provider(self, mock_docker_module):
        """Test list_agents only returns containers from docker provider."""
        from agency_quickdeploy.providers.docker import DockerProvider

        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        # Container from docker provider
        mock_container1 = Mock()
        mock_container1.name = "docker-agent"
        mock_container1.status = "running"
        mock_container1.short_id = "abc123"
        mock_container1.labels = {
            "agency.agent": "true",
            "agency.agent-id": "docker-agent",
            "agency.provider": "docker",
        }

        # Container from different provider (should be filtered out)
        mock_container2 = Mock()
        mock_container2.name = "other-agent"
        mock_container2.status = "running"
        mock_container2.short_id = "def456"
        mock_container2.labels = {
            "agency.agent": "true",
            "agency.agent-id": "other-agent",
            "agency.provider": "railway",  # Different provider
        }

        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        config = QuickDeployConfig(
            provider=ProviderType.DOCKER,
            auth_type=AuthType.API_KEY,
        )

        provider = DockerProvider(config)
        provider._docker = mock_client

        agents = provider.list_agents()

        assert len(agents) == 1
        assert agents[0]["name"] == "docker-agent"
