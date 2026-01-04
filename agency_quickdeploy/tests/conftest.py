"""Pytest fixtures for agency_quickdeploy tests."""
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_env_vars():
    """Fixture to set up and tear down environment variables."""
    original_env = os.environ.copy()

    def _set_env(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    yield _set_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_gcp_project():
    """Mock GCP project ID."""
    return "test-project-123"


@pytest.fixture
def mock_gcp_zone():
    """Mock GCP zone."""
    return "us-central1-a"


@pytest.fixture
def mock_gcs_bucket():
    """Mock GCS bucket name."""
    return "agency-quickdeploy-test-project-123"
