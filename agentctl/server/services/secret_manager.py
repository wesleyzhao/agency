"""GCP Secret Manager service."""
from typing import Optional
from google.cloud import secretmanager
from google.api_core import exceptions


class SecretManagerService:
    """Manage secrets in GCP Secret Manager."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self.parent = f"projects/{project_id}"

    def set_secret(self, secret_id: str, value: str) -> str:
        """Create or update a secret."""
        secret_name = f"{self.parent}/secrets/{secret_id}"

        # Create secret if doesn't exist
        try:
            self.client.create_secret(
                request={
                    "parent": self.parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except exceptions.AlreadyExists:
            pass

        # Add new version
        version = self.client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": value.encode("utf-8")},
            }
        )
        return version.name

    def get_secret(self, secret_id: str) -> Optional[str]:
        """Get latest secret value."""
        try:
            name = f"{self.parent}/secrets/{secret_id}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except exceptions.NotFound:
            return None

    def list_secrets(self) -> list[str]:
        """List all secret names."""
        secrets = self.client.list_secrets(request={"parent": self.parent})
        return [s.name.split("/")[-1] for s in secrets]
