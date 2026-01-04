"""GCP Secret Manager operations for agency-quickdeploy.

This module provides access to secrets stored in GCP Secret Manager.
"""
from typing import Optional

from google.cloud import secretmanager
from google.api_core.exceptions import NotFound


class SecretManager:
    """Access secrets from GCP Secret Manager."""

    def __init__(self, project: str):
        """Initialize secret manager client.

        Args:
            project: GCP project ID
        """
        self.project = project
        self._client = None

    @property
    def client(self) -> secretmanager.SecretManagerServiceClient:
        """Lazy-initialize secret manager client."""
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def get(self, name: str) -> Optional[str]:
        """Get latest version of a secret.

        Args:
            name: Secret name

        Returns:
            Secret value as string, or None if not found
        """
        try:
            secret_path = f"projects/{self.project}/secrets/{name}/versions/latest"
            response = self.client.access_secret_version(name=secret_path)
            return response.payload.data.decode("utf-8")
        except NotFound:
            return None

    def exists(self, name: str) -> bool:
        """Check if secret exists.

        Args:
            name: Secret name

        Returns:
            True if secret exists
        """
        try:
            secret_path = f"projects/{self.project}/secrets/{name}"
            self.client.get_secret(name=secret_path)
            return True
        except NotFound:
            return False
