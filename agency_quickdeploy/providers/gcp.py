"""GCP provider implementation for agency-quickdeploy.

This module wraps the existing GCP modules (VMManager, QuickDeployStorage)
to implement the BaseProvider interface.
"""

from typing import Optional, Any

from agency_quickdeploy.providers.base import BaseProvider, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import Credentials
from agency_quickdeploy.gcp.vm import VMManager
from agency_quickdeploy.gcp.storage import QuickDeployStorage
from shared.harness.startup_template import generate_startup_script


class GCPProvider(BaseProvider):
    """GCP provider using Compute Engine VMs.

    This provider launches agents as GCP Compute Engine VMs,
    using GCS for state storage.
    """

    def __init__(self, config: QuickDeployConfig):
        """Initialize GCP provider.

        Args:
            config: QuickDeploy configuration with GCP settings
        """
        self.config = config
        self._vm_manager: Optional[VMManager] = None
        self._storage: Optional[QuickDeployStorage] = None

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

    def launch(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> DeploymentResult:
        """Launch an agent on GCP Compute Engine.

        Args:
            agent_id: Unique identifier for the agent
            prompt: Task prompt for the agent
            credentials: Authentication credentials
            **kwargs: Additional options (repo, branch, spot, max_iterations, no_shutdown)

        Returns:
            DeploymentResult with launch status
        """
        try:
            # Ensure bucket exists
            self.storage.ensure_bucket(location=self.config.gcp_region)

            # Generate startup script
            startup_script = generate_startup_script(
                agent_id=agent_id,
                prompt=prompt,
                project=self.config.gcp_project,
                bucket=self.config.gcs_bucket,
                repo=kwargs.get("repo", ""),
                branch=kwargs.get("branch", ""),
                max_iterations=kwargs.get("max_iterations", 0),
                no_shutdown=kwargs.get("no_shutdown", False),
            )

            # Get VM metadata from credentials
            vm_metadata = credentials.get_vm_metadata() if credentials else {}

            # Create VM
            self.vm_manager.create(
                name=agent_id,
                machine_type=self.config.machine_type,
                startup_script=startup_script,
                metadata=vm_metadata,
                spot=kwargs.get("spot", False),
                labels={
                    "agency-quickdeploy": "true",
                    "agent-id": agent_id,
                },
            )

            return DeploymentResult(
                agent_id=agent_id,
                provider="gcp",
                status="launching",
            )

        except Exception as e:
            return DeploymentResult(
                agent_id=agent_id,
                provider="gcp",
                status="failed",
                error=str(e),
            )

    def status(self, agent_id: str) -> dict:
        """Get agent status from GCS and VM.

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
        """Get agent logs from GCS.

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
