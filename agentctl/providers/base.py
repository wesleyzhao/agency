"""Abstract cloud provider interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class VMConfig:
    """Configuration for creating a VM."""
    name: str
    machine_type: str
    startup_script: str
    spot: bool = False
    labels: dict = None


@dataclass
class VMInstance:
    """Represents a running VM."""
    name: str
    status: str  # "running", "stopped", "terminated"
    external_ip: Optional[str]
    provider_id: str  # Provider-specific ID


class CloudProvider(ABC):
    """Abstract interface for cloud operations.

    Implement this to add support for new cloud providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'gcp', 'aws', 'local')."""
        pass

    @abstractmethod
    def create_vm(self, config: VMConfig) -> VMInstance:
        """Create a new VM instance."""
        pass

    @abstractmethod
    def delete_vm(self, name: str) -> bool:
        """Delete a VM instance. Returns True if deleted."""
        pass

    @abstractmethod
    def get_vm(self, name: str) -> Optional[VMInstance]:
        """Get VM details. Returns None if not found."""
        pass

    @abstractmethod
    def list_vms(self, label_filter: dict = None) -> list[VMInstance]:
        """List VMs, optionally filtered by labels."""
        pass

    @abstractmethod
    def get_secret(self, name: str) -> Optional[str]:
        """Get a secret value. Returns None if not found."""
        pass

    @abstractmethod
    def set_secret(self, name: str, value: str) -> None:
        """Set a secret value."""
        pass

    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to cloud storage. Returns the cloud URL."""
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download file from cloud storage."""
        pass

    @abstractmethod
    def list_files(self, prefix: str) -> list[str]:
        """List files in cloud storage with given prefix."""
        pass
