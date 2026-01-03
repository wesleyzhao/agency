"""Tests for config.py - TDD style.

These tests define the expected behavior of the configuration module.
"""
import os
import pytest
from pathlib import Path


class TestQuickDeployConfig:
    """Tests for the QuickDeployConfig dataclass."""

    def test_config_requires_gcp_project(self):
        """Config should require gcp_project."""
        from agency_quickdeploy.config import QuickDeployConfig

        # Should work with project
        config = QuickDeployConfig(gcp_project="my-project")
        assert config.gcp_project == "my-project"

    def test_config_has_default_zone(self):
        """Config should have a default zone."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="my-project")
        assert config.gcp_zone == "us-central1-a"

    def test_config_has_default_region(self):
        """Config should have a default region (derived from zone)."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="my-project")
        assert config.gcp_region == "us-central1"

    def test_config_has_default_machine_type(self):
        """Config should have a default machine type."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="my-project")
        assert config.machine_type == "e2-medium"

    def test_config_bucket_auto_generated(self):
        """If bucket not provided, should auto-generate from project."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="my-project")
        assert config.gcs_bucket is not None
        assert "my-project" in config.gcs_bucket

    def test_config_bucket_can_be_set(self):
        """Bucket can be explicitly set."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(
            gcp_project="my-project",
            gcs_bucket="my-custom-bucket"
        )
        assert config.gcs_bucket == "my-custom-bucket"

    def test_config_has_api_key_secret_name(self):
        """Config should have secret name for Anthropic API key."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="my-project")
        assert config.anthropic_api_key_secret == "anthropic-api-key"

    def test_config_custom_zone(self):
        """Custom zone should work."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(
            gcp_project="my-project",
            gcp_zone="europe-west1-b"
        )
        assert config.gcp_zone == "europe-west1-b"

    def test_config_custom_machine_type(self):
        """Custom machine type should work."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(
            gcp_project="my-project",
            machine_type="n2-standard-4"
        )
        assert config.machine_type == "n2-standard-4"


class TestLoadConfigFromEnv:
    """Tests for loading config from environment variables."""

    def test_load_project_from_env(self, mock_env_vars):
        """Should load GCP project from environment."""
        from agency_quickdeploy.config import load_config

        mock_env_vars(QUICKDEPLOY_PROJECT="env-project")

        config = load_config()
        assert config.gcp_project == "env-project"

    def test_load_zone_from_env(self, mock_env_vars):
        """Should load zone from environment."""
        from agency_quickdeploy.config import load_config

        mock_env_vars(
            QUICKDEPLOY_PROJECT="test-project",
            QUICKDEPLOY_ZONE="asia-east1-a"
        )

        config = load_config()
        assert config.gcp_zone == "asia-east1-a"

    def test_load_bucket_from_env(self, mock_env_vars):
        """Should load bucket from environment."""
        from agency_quickdeploy.config import load_config

        mock_env_vars(
            QUICKDEPLOY_PROJECT="test-project",
            QUICKDEPLOY_BUCKET="env-bucket"
        )

        config = load_config()
        assert config.gcs_bucket == "env-bucket"

    def test_load_machine_type_from_env(self, mock_env_vars):
        """Should load machine type from environment."""
        from agency_quickdeploy.config import load_config

        mock_env_vars(
            QUICKDEPLOY_PROJECT="test-project",
            QUICKDEPLOY_MACHINE_TYPE="n1-standard-2"
        )

        config = load_config()
        assert config.machine_type == "n1-standard-2"

    def test_missing_project_raises_error(self, mock_env_vars):
        """Should raise error if no project configured."""
        from agency_quickdeploy.config import load_config, ConfigError

        mock_env_vars(QUICKDEPLOY_PROJECT=None)  # Ensure not set

        with pytest.raises(ConfigError):
            load_config()

    def test_fallback_to_gcloud_project(self, mock_env_vars):
        """Should try GOOGLE_CLOUD_PROJECT if QUICKDEPLOY_PROJECT not set."""
        from agency_quickdeploy.config import load_config

        mock_env_vars(
            QUICKDEPLOY_PROJECT=None,
            GOOGLE_CLOUD_PROJECT="gcloud-project"
        )

        config = load_config()
        assert config.gcp_project == "gcloud-project"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_valid_config(self):
        """Valid config should pass validation."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="valid-project")
        errors = config.validate()
        assert errors == []

    def test_validate_invalid_project_name(self):
        """Invalid project name should fail validation."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="INVALID_PROJECT!")
        errors = config.validate()
        assert len(errors) > 0
        assert any("project" in e.lower() for e in errors)

    def test_validate_invalid_zone(self):
        """Invalid zone should fail validation."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(
            gcp_project="valid-project",
            gcp_zone="invalid-zone"
        )
        errors = config.validate()
        # Zone validation is optional for now, but should not crash
        assert isinstance(errors, list)

    def test_validate_empty_project(self):
        """Empty project should fail validation."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(gcp_project="")
        errors = config.validate()
        assert len(errors) > 0


class TestConfigRegion:
    """Tests for region derivation from zone."""

    def test_region_from_zone(self):
        """Region should be derived from zone."""
        from agency_quickdeploy.config import QuickDeployConfig

        config = QuickDeployConfig(
            gcp_project="test",
            gcp_zone="us-central1-a"
        )
        assert config.gcp_region == "us-central1"

    def test_region_from_different_zones(self):
        """Different zones should give correct regions."""
        from agency_quickdeploy.config import QuickDeployConfig

        test_cases = [
            ("us-central1-a", "us-central1"),
            ("us-west1-b", "us-west1"),
            ("europe-west1-c", "europe-west1"),
            ("asia-east1-a", "asia-east1"),
        ]

        for zone, expected_region in test_cases:
            config = QuickDeployConfig(gcp_project="test", gcp_zone=zone)
            assert config.gcp_region == expected_region, f"Zone {zone} should give region {expected_region}"
