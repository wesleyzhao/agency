"""Tests for gcp/storage.py - TDD style.

These tests define the expected behavior of the GCS storage module.
Tests use mocks to avoid requiring actual GCP credentials.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestQuickDeployStorage:
    """Tests for QuickDeployStorage class."""

    def test_init_with_bucket_and_project(self):
        """Should initialize with bucket name and project."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        storage = QuickDeployStorage(
            bucket_name="my-bucket",
            project="my-project"
        )
        assert storage.bucket_name == "my-bucket"
        assert storage.project == "my-project"

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_ensure_bucket_creates_if_not_exists(self, mock_client_class):
        """Should create bucket if it doesn't exist."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Bucket doesn't exist - raises NotFound
        from google.api_core.exceptions import NotFound
        mock_client.get_bucket.side_effect = NotFound("Bucket not found")

        storage = QuickDeployStorage("test-bucket", "test-project")
        result = storage.ensure_bucket()

        assert result is True
        mock_client.create_bucket.assert_called_once()

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_ensure_bucket_returns_true_if_exists(self, mock_client_class):
        """Should return True if bucket already exists."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Bucket exists
        mock_bucket = MagicMock()
        mock_client.get_bucket.return_value = mock_bucket

        storage = QuickDeployStorage("test-bucket", "test-project")
        result = storage.ensure_bucket()

        assert result is True
        mock_client.create_bucket.assert_not_called()

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_upload_file(self, mock_client_class):
        """Should upload file to GCS."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage
        from pathlib import Path
        import tempfile

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            local_path = Path(f.name)

        try:
            storage = QuickDeployStorage("test-bucket", "test-project")
            result = storage.upload(local_path, "remote/path.txt")

            assert "gs://" in result
            mock_blob.upload_from_filename.assert_called_once()
        finally:
            local_path.unlink()

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_download_file(self, mock_client_class):
        """Should download file content from GCS."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.download_as_text.return_value = "file content here"

        storage = QuickDeployStorage("test-bucket", "test-project")
        content = storage.download("remote/file.txt")

        assert content == "file content here"

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_download_missing_file_returns_none(self, mock_client_class):
        """Should return None if file doesn't exist."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage
        from google.api_core.exceptions import NotFound

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.download_as_text.side_effect = NotFound("Not found")

        storage = QuickDeployStorage("test-bucket", "test-project")
        content = storage.download("nonexistent.txt")

        assert content is None


class TestAgentStateOperations:
    """Tests for agent-specific state operations."""

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_get_agent_status(self, mock_client_class):
        """Should read agent status from GCS."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.download_as_text.return_value = "running"

        storage = QuickDeployStorage("test-bucket", "test-project")
        status = storage.get_agent_status("agent-123")

        assert status["status"] == "running"

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_get_agent_status_includes_feature_list(self, mock_client_class):
        """Should include feature list in agent status if available."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage
        import json

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        def mock_blob_download(blob_path):
            mock_blob = MagicMock()
            if "status" in blob_path:
                mock_blob.download_as_text.return_value = "running"
            elif "feature_list" in blob_path:
                mock_blob.download_as_text.return_value = json.dumps({
                    "features": [
                        {"id": 1, "status": "completed"},
                        {"id": 2, "status": "pending"},
                    ]
                })
            else:
                from google.api_core.exceptions import NotFound
                mock_blob.download_as_text.side_effect = NotFound("Not found")
            return mock_blob

        mock_bucket.blob.side_effect = mock_blob_download

        storage = QuickDeployStorage("test-bucket", "test-project")
        status = storage.get_agent_status("agent-123")

        assert status["status"] == "running"
        assert "features" in status or "feature_count" in status

    @patch("agency_quickdeploy.gcp.storage.storage.Client")
    def test_list_agents(self, mock_client_class):
        """Should list all agent directories in bucket."""
        from agency_quickdeploy.gcp.storage import QuickDeployStorage

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock blobs with name attribute
        mock_blob1 = MagicMock()
        mock_blob1.name = "agents/agent-001/status"
        mock_blob2 = MagicMock()
        mock_blob2.name = "agents/agent-002/status"
        mock_blob3 = MagicMock()
        mock_blob3.name = "agents/agent-003/feature_list.json"

        mock_client.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]

        storage = QuickDeployStorage("test-bucket", "test-project")
        agents = storage.list_agents()

        # Should return unique agent IDs
        assert len(agents) == 3  # agent-001, agent-002, agent-003
