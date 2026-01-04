"""Configuration management for agency-quickdeploy.

This module provides configuration loading and validation for the
agency-quickdeploy CLI tool.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from agency_quickdeploy.auth import AuthType


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def load_dotenv(path: str = ".env") -> None:
    """Load environment variables from a .env file.

    Simple implementation without external dependencies.
    Supports: KEY=value format, comments (#), empty lines.

    Args:
        path: Path to .env file (default: .env in current directory)
    """
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=value
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ[key] = value
    except FileNotFoundError:
        # .env file doesn't exist, that's fine
        pass


@dataclass
class QuickDeployConfig:
    """Configuration for agency-quickdeploy operations.

    Attributes:
        gcp_project: GCP project ID (required)
        gcp_zone: GCP zone for VM creation
        gcp_region: GCP region (derived from zone)
        gcs_bucket: GCS bucket for state/logs (auto-generated if not set)
        machine_type: GCE machine type for VMs
        auth_type: Authentication type (api_key or oauth)
        anthropic_api_key_secret: Secret Manager secret name for API key
        oauth_credentials_secret: Secret Manager secret name for OAuth credentials
    """

    gcp_project: str
    gcp_zone: str = "us-central1-a"
    machine_type: str = "e2-medium"
    auth_type: AuthType = AuthType.API_KEY
    anthropic_api_key_secret: str = "anthropic-api-key"
    oauth_credentials_secret: str = "claude-oauth-credentials"
    gcs_bucket: Optional[str] = None

    @property
    def gcp_region(self) -> str:
        """Derive region from zone (e.g., us-central1-a -> us-central1)."""
        # Zone format: region-zone (e.g., us-central1-a)
        # Remove the last part after the final hyphen
        parts = self.gcp_zone.rsplit("-", 1)
        return parts[0] if len(parts) > 1 else self.gcp_zone

    def __post_init__(self):
        """Initialize derived fields."""
        # Auto-generate bucket name if not provided
        if self.gcs_bucket is None:
            self.gcs_bucket = f"agency-quickdeploy-{self.gcp_project}"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        # Validate project name
        if not self.gcp_project:
            errors.append("GCP project is required")
        elif not re.match(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$', self.gcp_project):
            # GCP project names must be 6-30 chars, lowercase, alphanumeric + hyphens
            # Must start with letter, end with letter or number
            if not re.match(r'^[a-z0-9-]+$', self.gcp_project.lower()):
                errors.append(f"Invalid GCP project name: {self.gcp_project}")

        return errors


def load_config(auth_type_override: Optional[str] = None) -> QuickDeployConfig:
    """Load configuration from environment variables.

    Environment variables:
        QUICKDEPLOY_PROJECT: GCP project ID
        QUICKDEPLOY_ZONE: GCP zone (default: us-central1-a)
        QUICKDEPLOY_BUCKET: GCS bucket name (auto-generated if not set)
        QUICKDEPLOY_MACHINE_TYPE: GCE machine type (default: e2-medium)
        QUICKDEPLOY_AUTH_TYPE: Authentication type (api_key or oauth)
        GOOGLE_CLOUD_PROJECT: Fallback for project if QUICKDEPLOY_PROJECT not set

    Args:
        auth_type_override: Override auth type from CLI (takes precedence over env)

    Returns:
        QuickDeployConfig instance

    Raises:
        ConfigError: If required configuration is missing
    """
    # Get project from env vars (try QUICKDEPLOY_PROJECT first, then GOOGLE_CLOUD_PROJECT)
    project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")

    if not project:
        raise ConfigError(
            "GCP project not configured. Set QUICKDEPLOY_PROJECT or GOOGLE_CLOUD_PROJECT environment variable."
        )

    # Get optional settings with defaults
    zone = os.environ.get("QUICKDEPLOY_ZONE", "us-central1-a")
    bucket = os.environ.get("QUICKDEPLOY_BUCKET")
    machine_type = os.environ.get("QUICKDEPLOY_MACHINE_TYPE", "e2-medium")

    # Determine auth type: CLI override > env var > default
    auth_type_str = auth_type_override or os.environ.get("QUICKDEPLOY_AUTH_TYPE", "api_key")
    try:
        auth_type = AuthType(auth_type_str.lower())
    except ValueError:
        raise ConfigError(
            f"Invalid auth type: {auth_type_str}. Must be 'api_key' or 'oauth'."
        )

    config = QuickDeployConfig(
        gcp_project=project,
        gcp_zone=zone,
        machine_type=machine_type,
        auth_type=auth_type,
    )

    if bucket:
        config.gcs_bucket = bucket

    return config
