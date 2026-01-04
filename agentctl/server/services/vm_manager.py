"""GCP Compute Engine VM management."""
import time
from typing import Optional
from google.cloud import compute_v1


class VMManager:
    """Manage GCE VM instances for agents."""

    def __init__(self, project: str, zone: str):
        self.project = project
        self.zone = zone
        self.client = compute_v1.InstancesClient()
        self.ops_client = compute_v1.ZoneOperationsClient()

    def create_instance(
        self,
        name: str,
        machine_type: str,
        startup_script: str,
        spot: bool = False,
        service_account: Optional[str] = None,
        labels: Optional[dict] = None,
        metadata_items: Optional[dict] = None,
    ) -> dict:
        """Create a new VM instance.

        Args:
            metadata_items: Additional metadata key-value pairs (e.g., API keys)
        """
        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = f"zones/{self.zone}/machineTypes/{machine_type}"

        # Boot disk - Ubuntu 22.04
        disk = compute_v1.AttachedDisk()
        disk.boot = True
        disk.auto_delete = True
        init_params = compute_v1.AttachedDiskInitializeParams()
        init_params.source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
        init_params.disk_size_gb = 50
        disk.initialize_params = init_params
        instance.disks = [disk]

        # Network with external IP
        network = compute_v1.NetworkInterface()
        network.network = "global/networks/default"
        access = compute_v1.AccessConfig()
        access.name = "External NAT"
        access.type_ = "ONE_TO_ONE_NAT"
        network.access_configs = [access]
        instance.network_interfaces = [network]

        # Metadata: startup script + any additional items (e.g., API keys)
        metadata = compute_v1.Metadata()
        items = [compute_v1.Items(key="startup-script", value=startup_script)]
        if metadata_items:
            for key, value in metadata_items.items():
                items.append(compute_v1.Items(key=key, value=value))
        metadata.items = items
        instance.metadata = metadata

        # Service account - always use cloud-platform scope for GCS access
        # VMs need write access to upload logs and progress files
        sa = compute_v1.ServiceAccount()
        if service_account:
            sa.email = service_account
        else:
            # Use default compute service account
            sa.email = "default"
        sa.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        instance.service_accounts = [sa]

        # Labels
        instance.labels = labels or {}
        instance.labels["agentctl"] = "true"

        # Spot instance
        if spot:
            sched = compute_v1.Scheduling()
            sched.preemptible = True
            sched.automatic_restart = False
            instance.scheduling = sched

        # Create and wait
        op = self.client.insert(project=self.project, zone=self.zone, instance_resource=instance)
        self._wait_for_operation(op.name)

        # Return instance info
        return self.get_instance(name)

    def get_instance(self, name: str) -> Optional[dict]:
        """Get instance details."""
        try:
            inst = self.client.get(project=self.project, zone=self.zone, instance=name)
            return {
                "name": inst.name,
                "status": inst.status,
                "external_ip": self._get_external_ip(inst),
                "machine_type": inst.machine_type.split("/")[-1],
            }
        except Exception:
            return None

    def delete_instance(self, name: str) -> bool:
        """Delete a VM instance."""
        try:
            op = self.client.delete(project=self.project, zone=self.zone, instance=name)
            self._wait_for_operation(op.name)
            return True
        except Exception:
            return False

    def list_instances(self, label_filter: Optional[dict] = None) -> list[dict]:
        """List VM instances with optional label filter."""
        try:
            request = compute_v1.ListInstancesRequest(
                project=self.project,
                zone=self.zone,
            )
            if label_filter:
                filters = [f"labels.{k}={v}" for k, v in label_filter.items()]
                request.filter = " AND ".join(filters)

            instances = self.client.list(request=request)
            return [
                {
                    "name": inst.name,
                    "status": inst.status,
                    "external_ip": self._get_external_ip(inst),
                    "machine_type": inst.machine_type.split("/")[-1],
                }
                for inst in instances
            ]
        except Exception:
            return []

    def _get_external_ip(self, instance) -> Optional[str]:
        """Extract external IP from instance."""
        for iface in instance.network_interfaces:
            for config in iface.access_configs:
                if config.nat_i_p:
                    return config.nat_i_p
        return None

    def _wait_for_operation(self, operation_name: str, timeout: int = 300):
        """Wait for a zone operation to complete."""
        start = time.time()
        while time.time() - start < timeout:
            op = self.ops_client.get(project=self.project, zone=self.zone, operation=operation_name)
            if op.status == compute_v1.Operation.Status.DONE:
                if op.error:
                    raise Exception(f"Operation failed: {op.error}")
                return
            time.sleep(2)
        raise TimeoutError(f"Operation {operation_name} timed out")
