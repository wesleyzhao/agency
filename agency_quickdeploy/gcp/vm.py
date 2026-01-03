"""GCE VM management for agency-quickdeploy.

This module provides VM creation, deletion, and management for agent VMs.
"""
from typing import Optional

from google.cloud import compute_v1
from google.api_core.exceptions import NotFound


class VMManager:
    """Manages GCP Compute Engine VMs for agency-quickdeploy.

    Each agent runs in its own VM with:
    - Ubuntu 22.04 LTS
    - 50GB boot disk
    - External IP for SSH access
    - Labels for tracking: agency-quickdeploy=true
    """

    def __init__(self, project: str, zone: str):
        """Initialize VM manager.

        Args:
            project: GCP project ID
            zone: GCP zone (e.g., us-central1-a)
        """
        self.project = project
        self.zone = zone
        self._instances_client = None
        self._ops_client = None

    @property
    def instances_client(self) -> compute_v1.InstancesClient:
        """Lazy-initialize instances client."""
        if self._instances_client is None:
            self._instances_client = compute_v1.InstancesClient()
        return self._instances_client

    @property
    def ops_client(self) -> compute_v1.ZoneOperationsClient:
        """Lazy-initialize operations client."""
        if self._ops_client is None:
            self._ops_client = compute_v1.ZoneOperationsClient()
        return self._ops_client

    def create(
        self,
        name: str,
        machine_type: str,
        startup_script: str,
        metadata: dict,
        spot: bool = False,
        labels: Optional[dict] = None,
        disk_size_gb: int = 50,
    ) -> dict:
        """Create a VM instance.

        Args:
            name: Instance name
            machine_type: GCE machine type (e.g., e2-medium)
            startup_script: Bash startup script
            metadata: Instance metadata (for secrets)
            spot: Use spot/preemptible instance
            labels: Instance labels for tracking
            disk_size_gb: Boot disk size

        Returns:
            Dict with instance info
        """
        # Default labels
        instance_labels = {
            "agency-quickdeploy": "true",
        }
        if labels:
            instance_labels.update(labels)

        # Build instance metadata
        instance_metadata = compute_v1.Metadata()
        instance_metadata.items = []

        # Add startup script
        startup_item = compute_v1.Items()
        startup_item.key = "startup-script"
        startup_item.value = startup_script
        instance_metadata.items.append(startup_item)

        # Add other metadata (e.g., API keys)
        for key, value in metadata.items():
            item = compute_v1.Items()
            item.key = key
            item.value = value
            instance_metadata.items.append(item)

        # Build boot disk
        disk = compute_v1.AttachedDisk()
        disk.auto_delete = True
        disk.boot = True
        disk.type_ = "PERSISTENT"

        disk_init = compute_v1.AttachedDiskInitializeParams()
        disk_init.disk_size_gb = disk_size_gb
        disk_init.source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
        disk.initialize_params = disk_init

        # Build network interface with external IP
        network = compute_v1.NetworkInterface()
        network.network = "global/networks/default"

        access_config = compute_v1.AccessConfig()
        access_config.type_ = "ONE_TO_ONE_NAT"
        access_config.name = "External NAT"
        network.access_configs = [access_config]

        # Build instance
        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = f"zones/{self.zone}/machineTypes/{machine_type}"
        instance.disks = [disk]
        instance.network_interfaces = [network]
        instance.metadata = instance_metadata
        instance.labels = instance_labels

        # Configure spot/preemptible if requested
        if spot:
            scheduling = compute_v1.Scheduling()
            scheduling.provisioning_model = "SPOT"
            scheduling.instance_termination_action = "DELETE"
            instance.scheduling = scheduling

        # Add service account for GCS access
        service_account = compute_v1.ServiceAccount()
        service_account.email = "default"
        service_account.scopes = [
            "https://www.googleapis.com/auth/cloud-platform",
        ]
        instance.service_accounts = [service_account]

        # Create instance
        operation = self.instances_client.insert(
            project=self.project,
            zone=self.zone,
            instance_resource=instance,
        )

        # Wait for operation to complete
        self.ops_client.wait(
            project=self.project,
            zone=self.zone,
            operation=operation.name,
        )

        return {
            "name": name,
            "zone": self.zone,
            "project": self.project,
            "status": "creating",
        }

    def delete(self, name: str) -> bool:
        """Delete a VM instance.

        Args:
            name: Instance name

        Returns:
            True if deleted successfully
        """
        try:
            operation = self.instances_client.delete(
                project=self.project,
                zone=self.zone,
                instance=name,
            )

            # Wait for operation to complete
            self.ops_client.wait(
                project=self.project,
                zone=self.zone,
                operation=operation.name,
            )

            return True
        except NotFound:
            return True  # Already deleted

    def get(self, name: str) -> Optional[dict]:
        """Get VM instance details.

        Args:
            name: Instance name

        Returns:
            Dict with instance info, or None if not found
        """
        try:
            instance = self.instances_client.get(
                project=self.project,
                zone=self.zone,
                instance=name,
            )

            # Extract external IP if available
            external_ip = None
            if instance.network_interfaces:
                for nic in instance.network_interfaces:
                    if nic.access_configs:
                        for ac in nic.access_configs:
                            if ac.nat_i_p:
                                external_ip = ac.nat_i_p
                                break

            return {
                "name": instance.name,
                "status": instance.status,
                "zone": self.zone,
                "project": self.project,
                "external_ip": external_ip,
                "machine_type": instance.machine_type,
            }
        except NotFound:
            return None

    def list_by_label(self, label_key: str, label_value: str) -> list[dict]:
        """List VMs with specific label.

        Args:
            label_key: Label key to filter by
            label_value: Label value to match

        Returns:
            List of instance dicts
        """
        # Use filter for labels
        filter_str = f"labels.{label_key}={label_value}"

        request = compute_v1.ListInstancesRequest(
            project=self.project,
            zone=self.zone,
            filter=filter_str,
        )
        instances = self.instances_client.list(request=request)

        result = []
        for instance in instances:
            # Extract external IP if available
            external_ip = None
            if instance.network_interfaces:
                for nic in instance.network_interfaces:
                    if nic.access_configs:
                        for ac in nic.access_configs:
                            if ac.nat_i_p:
                                external_ip = ac.nat_i_p
                                break

            result.append({
                "name": instance.name,
                "status": instance.status,
                "external_ip": external_ip,
            })

        return result
