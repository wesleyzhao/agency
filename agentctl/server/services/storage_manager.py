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

    def grant_compute_access(self) -> bool:
        """Grant the default compute service account access to this bucket.

        This is required for VMs to write logs and progress files to GCS.
        """
        try:
            # Get project number from client
            project_number = self._get_project_number()
            if not project_number:
                return False

            service_account = f"{project_number}-compute@developer.gserviceaccount.com"

            # Get current policy
            bucket = self.client.get_bucket(self.bucket_name)
            policy = bucket.get_iam_policy(requested_policy_version=3)

            # Add objectCreator and objectViewer roles
            policy.bindings.append({
                "role": "roles/storage.objectCreator",
                "members": {f"serviceAccount:{service_account}"},
            })
            policy.bindings.append({
                "role": "roles/storage.objectViewer",
                "members": {f"serviceAccount:{service_account}"},
            })

            bucket.set_iam_policy(policy)
            return True
        except Exception:
            return False

    def _get_project_number(self) -> Optional[str]:
        """Get the project number from the project ID."""
        try:
            from google.cloud import resourcemanager_v3
            client = resourcemanager_v3.ProjectsClient()
            project = client.get_project(name=f"projects/{self.project}")
            # Project name is "projects/PROJECT_NUMBER"
            return project.name.split("/")[-1]
        except Exception:
            return None

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
