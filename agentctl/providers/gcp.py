"""GCP provider implementation - placeholder for Phase 3."""
from pathlib import Path
from typing import Optional

from agentctl.providers.base import CloudProvider, VMConfig, VMInstance


class GCPProvider(CloudProvider):
    """Google Cloud Platform provider.

    Full implementation in Phase 3.
    """

    name = "gcp"

    def __init__(self, project_id: str, zone: str = "us-central1-a"):
        self.project_id = project_id
        self.zone = zone

    def create_vm(self, config: VMConfig) -> VMInstance:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def delete_vm(self, name: str) -> bool:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def get_vm(self, name: str) -> Optional[VMInstance]:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def list_vms(self, label_filter: dict = None) -> list[VMInstance]:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def get_secret(self, name: str) -> Optional[str]:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def set_secret(self, name: str, value: str) -> None:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def upload_file(self, local_path: Path, remote_path: str) -> str:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def download_file(self, remote_path: str, local_path: Path) -> None:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")

    def list_files(self, prefix: str) -> list[str]:
        raise NotImplementedError("GCP provider will be implemented in Phase 3")
