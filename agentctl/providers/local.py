"""Local provider for development without cloud."""
from pathlib import Path
from typing import Optional
import json
import subprocess

from agentctl.providers.base import CloudProvider, VMConfig, VMInstance


class LocalProvider(CloudProvider):
    """Local development provider using Docker.

    This allows testing without a GCP account.
    """

    name = "local"

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".agentctl" / "local"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_file = self.data_dir / "secrets.json"
        self.storage_dir = self.data_dir / "storage"
        self.storage_dir.mkdir(exist_ok=True)

    def create_vm(self, config: VMConfig) -> VMInstance:
        """Create a Docker container as a 'VM'."""
        # For local dev, we might just run in a subprocess
        # or use Docker. Keeping simple for now.
        return VMInstance(
            name=config.name,
            status="running",
            external_ip="127.0.0.1",
            provider_id=f"local-{config.name}"
        )

    def delete_vm(self, name: str) -> bool:
        return True  # No-op for local

    def get_vm(self, name: str) -> Optional[VMInstance]:
        return None  # Would check Docker

    def list_vms(self, label_filter: dict = None) -> list[VMInstance]:
        return []

    def get_secret(self, name: str) -> Optional[str]:
        if not self.secrets_file.exists():
            return None
        secrets = json.loads(self.secrets_file.read_text())
        return secrets.get(name)

    def set_secret(self, name: str, value: str) -> None:
        secrets = {}
        if self.secrets_file.exists():
            secrets = json.loads(self.secrets_file.read_text())
        secrets[name] = value
        self.secrets_file.write_text(json.dumps(secrets, indent=2))

    def upload_file(self, local_path: Path, remote_path: str) -> str:
        dest = self.storage_dir / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(local_path.read_bytes())
        return f"local://{remote_path}"

    def download_file(self, remote_path: str, local_path: Path) -> None:
        src = self.storage_dir / remote_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(src.read_bytes())

    def list_files(self, prefix: str) -> list[str]:
        prefix_path = self.storage_dir / prefix
        if not prefix_path.exists():
            return []
        return [str(p.relative_to(self.storage_dir)) for p in prefix_path.rglob("*") if p.is_file()]
