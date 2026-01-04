"""GCS storage operations for agency-quickdeploy.

This module provides storage operations for agent state and logs.
"""
import json
from pathlib import Path
from typing import Optional

from google.cloud import storage
from google.api_core.exceptions import NotFound


class QuickDeployStorage:
    """GCS storage for agent state and logs.

    All agent state is stored in GCS, not a master server:
    - status: Agent status (starting, running, completed, failed)
    - feature_list.json: Feature tracking
    - claude-progress.txt: Progress notes
    - logs/: Agent execution logs
    """

    def __init__(self, bucket_name: str, project: str):
        """Initialize storage client.

        Args:
            bucket_name: GCS bucket name
            project: GCP project ID
        """
        self.bucket_name = bucket_name
        self.project = project
        self._client = None

    @property
    def client(self) -> storage.Client:
        """Lazy-initialize storage client."""
        if self._client is None:
            self._client = storage.Client(project=self.project)
        return self._client

    def ensure_bucket(self, location: str = "us-central1") -> bool:
        """Ensure bucket exists, creating if necessary.

        Args:
            location: GCS bucket location

        Returns:
            True if bucket exists or was created
        """
        try:
            self.client.get_bucket(self.bucket_name)
            return True
        except NotFound:
            bucket = self.client.create_bucket(
                self.bucket_name,
                location=location
            )
            return True

    def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload file to GCS.

        Args:
            local_path: Local file path
            remote_path: Remote path in bucket

        Returns:
            GCS URI (gs://bucket/path)
        """
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_path}"

    def download(self, remote_path: str) -> Optional[str]:
        """Download file content from GCS.

        Args:
            remote_path: Remote path in bucket

        Returns:
            File content as string, or None if not found
        """
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)
            return blob.download_as_text()
        except NotFound:
            return None

    def get_agent_status(self, agent_id: str) -> dict:
        """Get agent status and metadata from GCS.

        Args:
            agent_id: Agent identifier

        Returns:
            Dict with status, feature_count, etc.
        """
        result = {
            "agent_id": agent_id,
            "status": "unknown",
        }

        # Get status file
        status_content = self.download(f"agents/{agent_id}/status")
        if status_content:
            result["status"] = status_content.strip()

        # Get feature list if available
        feature_content = self.download(f"agents/{agent_id}/feature_list.json")
        if feature_content:
            try:
                features = json.loads(feature_content)
                feature_list = features.get("features", [])
                result["feature_count"] = len(feature_list)
                result["features_completed"] = sum(
                    1 for f in feature_list if f.get("status") == "completed"
                )
                result["features_pending"] = sum(
                    1 for f in feature_list if f.get("status") == "pending"
                )
            except json.JSONDecodeError:
                pass

        # Get progress notes if available
        progress_content = self.download(f"agents/{agent_id}/claude-progress.txt")
        if progress_content:
            result["has_progress"] = True

        return result

    def list_agents(self) -> list[str]:
        """List all agent IDs in the bucket.

        Returns:
            List of agent IDs
        """
        agent_ids = set()

        blobs = self.client.list_blobs(
            self.bucket_name,
            prefix="agents/"
        )

        for blob in blobs:
            # Extract agent ID from path like "agents/{agent_id}/..."
            parts = blob.name.split("/")
            if len(parts) >= 2:
                agent_ids.add(parts[1])

        return sorted(list(agent_ids))
