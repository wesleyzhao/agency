"""Base provider interface for agency-quickdeploy.

This module defines the abstract base class that all deployment providers
(GCP, Railway, etc.) must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

from agency_quickdeploy.auth import Credentials


class ProviderType(Enum):
    """Supported deployment providers."""

    GCP = "gcp"
    RAILWAY = "railway"
    AWS = "aws"
    DOCKER = "docker"


@dataclass
class DeploymentResult:
    """Result of a deployment operation.

    Attributes:
        agent_id: Unique identifier for the agent
        provider: Name of the provider (gcp, railway, etc.)
        status: Current status (launching, running, completed, failed)
        external_url: Optional external URL to access the agent
        error: Optional error message if deployment failed
    """

    agent_id: str
    provider: str
    status: str
    external_url: Optional[str] = None
    error: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for deployment providers.

    All deployment providers (GCP, Railway, etc.) must implement this interface
    to provide a consistent API for the launcher.
    """

    @abstractmethod
    def launch(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> DeploymentResult:
        """Launch a new agent on this provider.

        Args:
            agent_id: Unique identifier for the agent
            prompt: Task prompt for the agent
            credentials: Authentication credentials
            **kwargs: Provider-specific options (repo, branch, spot, etc.)

        Returns:
            DeploymentResult with status information
        """
        pass

    @abstractmethod
    def status(self, agent_id: str) -> dict:
        """Get the current status of an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dict with status information (status, vm_status, external_ip, etc.)
        """
        pass

    @abstractmethod
    def logs(self, agent_id: str) -> Optional[str]:
        """Get logs for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not available
        """
        pass

    @abstractmethod
    def stop(self, agent_id: str) -> bool:
        """Stop an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def list_agents(self) -> list[dict]:
        """List all agents managed by this provider.

        Returns:
            List of agent dicts with name, status, etc.
        """
        pass
