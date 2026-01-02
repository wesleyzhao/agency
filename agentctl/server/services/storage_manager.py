"""GCP Cloud Storage service."""
from pathlib import Path
from typing import Optional
from google.cloud import storage
from google.api_core import exceptions


class StorageManager:
    """Manage GCS bucket for agent artifacts."""

    def __init__(self, bucket_name: str, project: Optional[str] = None):
        self.client = storage.Client(project=project)
        self.bucket_name = bucket_name
        self.project = project
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def create_bucket(self, location: str = "us-central1") -> bool:
        """Create the bucket if it doesn't exist."""
        try:
            self.client.create_bucket(self.bucket_name, location=location)
            return True
        except exceptions.Conflict:
            return False  # Already exists

    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload a file to GCS."""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_path}"

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from GCS."""
        blob = self.bucket.blob(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))

    def list_files(self, prefix: str = "") -> list[str]:
        """List files with given prefix."""
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def delete_files(self, prefix: str) -> int:
        """Delete all files with prefix. Returns count deleted."""
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        return len(blobs)
