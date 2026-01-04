"""Main orchestration for agency-quickdeploy.

This module ties together all components to launch and manage agents.
"""
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.gcp.vm import VMManager
from agency_quickdeploy.gcp.storage import QuickDeployStorage
from agency_quickdeploy.gcp.secrets import SecretManager
from shared.harness.startup_template import generate_startup_script


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
    """Orchestrates launching Claude Code agents on GCP.

    This class:
    1. Ensures GCS bucket exists
    2. Gets API key from Secret Manager
    3. Generates startup script
    4. Creates VM with startup script
    5. Returns launch result
    """

    def __init__(self, config: QuickDeployConfig):
        """Initialize launcher with config.

        Args:
            config: QuickDeploy configuration
        """
        self.config = config
        self._vm_manager = None
        self._storage = None
        self._secrets = None

    @property
    def vm_manager(self) -> VMManager:
        """Lazy-initialize VM manager."""
        if self._vm_manager is None:
            self._vm_manager = VMManager(
                project=self.config.gcp_project,
                zone=self.config.gcp_zone,
            )
        return self._vm_manager

    @property
    def storage(self) -> QuickDeployStorage:
        """Lazy-initialize storage."""
        if self._storage is None:
            self._storage = QuickDeployStorage(
                bucket_name=self.config.gcs_bucket,
                project=self.config.gcp_project,
            )
        return self._storage

    @property
    def secrets(self) -> SecretManager:
        """Lazy-initialize secret manager."""
        if self._secrets is None:
            self._secrets = SecretManager(project=self.config.gcp_project)
        return self._secrets

    def _generate_agent_id(self) -> str:
        """Generate unique agent ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"agent-{timestamp}-{short_uuid}"

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

        try:
            # Ensure bucket exists
            self.storage.ensure_bucket(location=self.config.gcp_region)

            # Get API key: prefer env var, fall back to Secret Manager
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                # Fall back to Secret Manager
                api_key = self.secrets.get(self.config.anthropic_api_key_secret)

            if not api_key:
                return LaunchResult(
                    agent_id=agent_id,
                    vm_name=agent_id,
                    zone=self.config.gcp_zone,
                    project=self.config.gcp_project,
                    gcs_bucket=self.config.gcs_bucket,
                    status="failed",
                    error="API key not found. Set ANTHROPIC_API_KEY env var or store in Secret Manager.",
                )

            # Generate startup script
            startup_script = generate_startup_script(
                agent_id=agent_id,
                prompt=prompt,
                project=self.config.gcp_project,
                bucket=self.config.gcs_bucket,
                repo=repo or "",
                branch=branch or "",
                max_iterations=max_iterations,
                no_shutdown=no_shutdown,
            )

            # Create VM
            vm_result = self.vm_manager.create(
                name=agent_id,
                machine_type=self.config.machine_type,
                startup_script=startup_script,
                metadata={
                    "anthropic-api-key": api_key,
                },
                spot=spot,
                labels={
                    "agency-quickdeploy": "true",
                    "agent-id": agent_id,
                },
            )

            return LaunchResult(
                agent_id=agent_id,
                vm_name=vm_result.get("name", agent_id),
                zone=self.config.gcp_zone,
                project=self.config.gcp_project,
                gcs_bucket=self.config.gcs_bucket,
                status="launching",
            )

        except Exception as e:
            return LaunchResult(
                agent_id=agent_id,
                vm_name=agent_id,
                zone=self.config.gcp_zone,
                project=self.config.gcp_project,
                gcs_bucket=self.config.gcs_bucket,
                status="failed",
                error=str(e),
            )

    def status(self, agent_id: str) -> dict:
        """Get agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with agent info
        """
        # Get status from GCS
        gcs_status = self.storage.get_agent_status(agent_id)

        # Get VM status
        vm_info = self.vm_manager.get(agent_id)
        if vm_info:
            gcs_status["vm_status"] = vm_info.get("status")
            gcs_status["external_ip"] = vm_info.get("external_ip")

        return gcs_status

    def logs(self, agent_id: str) -> Optional[str]:
        """Get agent logs.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not found
        """
        return self.storage.download(f"agents/{agent_id}/logs/agent.log")

    def stop(self, agent_id: str) -> bool:
        """Stop an agent by deleting its VM.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully
        """
        return self.vm_manager.delete(agent_id)

    def list_agents(self) -> list[dict]:
        """List all quickdeploy agents.

        Returns:
            List of agent dicts
        """
        return self.vm_manager.list_by_label("agency-quickdeploy", "true")
