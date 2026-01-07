"""Main orchestration for agency-quickdeploy.

This module ties together all components to launch and manage agents.
"""
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import AuthType, Credentials, OAuthCredentials
from agency_quickdeploy.providers import BaseProvider, ProviderType


@dataclass
class LaunchResult:
    """Result of launching an agent."""
    agent_id: str
    vm_name: str
    zone: str
    project: str
    gcs_bucket: str
    status: str
    external_ip: Optional[str] = None
    error: Optional[str] = None


class QuickDeployLauncher:
    """Orchestrates launching Claude Code agents.

    This class:
    1. Initializes the appropriate provider (GCP, Railway, etc.)
    2. Gets credentials
    3. Delegates to provider for launch/status/stop operations
    """

    def __init__(self, config: QuickDeployConfig):
        """Initialize launcher with config.

        Args:
            config: QuickDeploy configuration
        """
        self.config = config
        self._provider: Optional[BaseProvider] = None
        self._secrets = None

    @property
    def provider(self) -> BaseProvider:
        """Lazy-initialize the deployment provider."""
        if self._provider is None:
            if self.config.provider == ProviderType.GCP:
                from agency_quickdeploy.providers.gcp import GCPProvider
                self._provider = GCPProvider(self.config)
            elif self.config.provider == ProviderType.RAILWAY:
                from agency_quickdeploy.providers.railway import RailwayProvider
                self._provider = RailwayProvider(self.config)
            elif self.config.provider == ProviderType.AWS:
                from agency_quickdeploy.providers.aws import AWSProvider
                self._provider = AWSProvider(self.config)
            elif self.config.provider == ProviderType.DOCKER:
                from agency_quickdeploy.providers.docker import DockerProvider
                self._provider = DockerProvider(self.config)
            else:
                raise ValueError(f"Unknown provider: {self.config.provider}")
        return self._provider

    @property
    def secrets(self):
        """Lazy-initialize secret manager (GCP only)."""
        if self._secrets is None and self.config.provider == ProviderType.GCP:
            from agency_quickdeploy.gcp.secrets import SecretManager
            self._secrets = SecretManager(project=self.config.gcp_project)
        return self._secrets

    def _generate_agent_id(self) -> str:
        """Generate unique agent ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"agent-{timestamp}-{short_uuid}"

    def _get_credentials(self) -> Optional[Credentials]:
        """Get credentials based on configured auth type.

        For API key auth:
            1. Check ANTHROPIC_API_KEY env var
            2. Fall back to Secret Manager (GCP only)

        For OAuth auth:
            1. Check CLAUDE_CODE_OAUTH_TOKEN env var
            2. Fall back to Secret Manager (GCP only)

        Returns:
            Credentials object or None if not found
        """
        if self.config.auth_type == AuthType.OAUTH:
            return self._get_oauth_credentials()
        else:
            return self._get_api_key_credentials()

    def _get_api_key_credentials(self) -> Optional[Credentials]:
        """Get API key credentials."""
        # Try env var first
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            return Credentials.from_api_key(api_key)

        # Fall back to Secret Manager (GCP only)
        if self.secrets:
            api_key = self.secrets.get(self.config.anthropic_api_key_secret)
            if api_key:
                return Credentials.from_api_key(api_key)

        return None

    def _get_oauth_credentials(self) -> Optional[Credentials]:
        """Get OAuth credentials."""
        # Try env var first (just the token)
        oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if oauth_token:
            oauth = OAuthCredentials(access_token=oauth_token)
            return Credentials.from_oauth(oauth)

        # Fall back to Secret Manager (GCP only)
        if self.secrets:
            credentials_json = self.secrets.get(self.config.oauth_credentials_secret)
            if credentials_json:
                return Credentials.from_oauth_json(credentials_json)

        return None

    def launch(
        self,
        prompt: str,
        name: Optional[str] = None,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        spot: bool = False,
        max_iterations: int = 0,
        no_shutdown: bool = False,
    ) -> LaunchResult:
        """Launch a new agent.

        Args:
            prompt: Task prompt for the agent
            name: Optional custom agent name
            repo: Git repository to clone
            branch: Git branch to use
            spot: Use spot/preemptible instance
            max_iterations: Max iterations (0 = unlimited)
            no_shutdown: Keep VM running after agent completes (for inspection)

        Returns:
            LaunchResult with agent info
        """
        # Generate agent ID
        agent_id = name or self._generate_agent_id()

        # Get credentials
        credentials = self._get_credentials()
        if credentials is None:
            if self.config.auth_type == AuthType.OAUTH:
                error_msg = (
                    "OAuth credentials not found. Either:\n"
                    "  1. Set CLAUDE_CODE_OAUTH_TOKEN env var, or\n"
                    f"  2. Store credentials in Secret Manager as '{self.config.oauth_credentials_secret}'"
                )
            else:
                error_msg = (
                    "API key not found. Either:\n"
                    "  1. Set ANTHROPIC_API_KEY env var, or\n"
                    f"  2. Store in Secret Manager as '{self.config.anthropic_api_key_secret}'"
                )
            return LaunchResult(
                agent_id=agent_id,
                vm_name=agent_id,
                zone=self.config.gcp_zone,
                project=self.config.gcp_project or "",
                gcs_bucket=self.config.gcs_bucket or "",
                status="failed",
                error=error_msg,
            )

        # Delegate to provider
        result = self.provider.launch(
            agent_id=agent_id,
            prompt=prompt,
            credentials=credentials,
            repo=repo,
            branch=branch,
            spot=spot,
            max_iterations=max_iterations,
            no_shutdown=no_shutdown,
        )

        # Convert DeploymentResult to LaunchResult for backward compatibility
        return LaunchResult(
            agent_id=result.agent_id,
            vm_name=result.agent_id,
            zone=self.config.gcp_zone,
            project=self.config.gcp_project or "",
            gcs_bucket=self.config.gcs_bucket or "",
            status=result.status,
            external_ip=result.external_url,
            error=result.error,
        )

    def status(self, agent_id: str) -> dict:
        """Get agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with agent info
        """
        return self.provider.status(agent_id)

    def logs(self, agent_id: str) -> Optional[str]:
        """Get agent logs.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not found
        """
        return self.provider.logs(agent_id)

    def stop(self, agent_id: str) -> bool:
        """Stop an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully
        """
        return self.provider.stop(agent_id)

    def list_agents(self) -> list[dict]:
        """List all quickdeploy agents.

        Returns:
            List of agent dicts
        """
        return self.provider.list_agents()
