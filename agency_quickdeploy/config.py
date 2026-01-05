"""Configuration management for agency-quickdeploy.

This module provides configuration loading and validation for the
agency-quickdeploy CLI tool.
"""
import os
import re
from dataclasses import dataclass
from typing import Optional

from agency_quickdeploy.auth import AuthType
from agency_quickdeploy.providers.base import ProviderType


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
        gcp_project: GCP project ID (required for GCP provider)
        gcp_zone: GCP zone for VM creation
        gcp_region: GCP region (derived from zone)
        gcs_bucket: GCS bucket for state/logs (auto-generated if not set)
        machine_type: GCE machine type for VMs
        auth_type: Authentication type (api_key or oauth)
        anthropic_api_key_secret: Secret Manager secret name for API key
        oauth_credentials_secret: Secret Manager secret name for OAuth credentials
        provider: Deployment provider (gcp or railway)
        railway_token: Railway API token (required for railway provider)
        railway_project_id: Railway project ID (auto-created if not set)
    """

    gcp_project: Optional[str] = None
    gcp_zone: str = "us-central1-a"
    machine_type: str = "e2-medium"
    auth_type: AuthType = AuthType.API_KEY
    anthropic_api_key_secret: str = "anthropic-api-key"
    oauth_credentials_secret: str = "claude-oauth-credentials"
    gcs_bucket: Optional[str] = None
    provider: ProviderType = ProviderType.GCP
    railway_token: Optional[str] = None
    railway_project_id: Optional[str] = None

    @property
    def gcp_region(self) -> str:
        """Derive region from zone (e.g., us-central1-a -> us-central1)."""
        # Zone format: region-zone (e.g., us-central1-a)
        # Remove the last part after the final hyphen
        parts = self.gcp_zone.rsplit("-", 1)
        return parts[0] if len(parts) > 1 else self.gcp_zone

    def __post_init__(self):
        """Initialize derived fields."""
        # Auto-generate bucket name if not provided (GCP only)
        if self.provider == ProviderType.GCP:
            if self.gcs_bucket is None and self.gcp_project:
                self.gcs_bucket = f"agency-quickdeploy-{self.gcp_project}"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        if self.provider == ProviderType.GCP:
            # Validate GCP-specific fields
            if not self.gcp_project:
                errors.append("GCP project is required for GCP provider")
            elif not re.match(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$', self.gcp_project):
                # GCP project names must be 6-30 chars, lowercase, alphanumeric + hyphens
                # Must start with letter, end with letter or number
                if not re.match(r'^[a-z0-9-]+$', self.gcp_project.lower()):
                    errors.append(f"Invalid GCP project name: {self.gcp_project}")
        elif self.provider == ProviderType.RAILWAY:
            # Validate Railway-specific fields
            if not self.railway_token:
                errors.append("RAILWAY_TOKEN is required for Railway provider")

        return errors


def load_config(
    auth_type_override: Optional[str] = None,
    provider_override: Optional[str] = None,
) -> QuickDeployConfig:
    """Load configuration from environment variables.

    Environment variables:
        QUICKDEPLOY_PROVIDER: Deployment provider (gcp or railway)
        QUICKDEPLOY_PROJECT: GCP project ID
        QUICKDEPLOY_ZONE: GCP zone (default: us-central1-a)
        QUICKDEPLOY_BUCKET: GCS bucket name (auto-generated if not set)
        QUICKDEPLOY_MACHINE_TYPE: GCE machine type (default: e2-medium)
        QUICKDEPLOY_AUTH_TYPE: Authentication type (api_key or oauth)
        GOOGLE_CLOUD_PROJECT: Fallback for project if QUICKDEPLOY_PROJECT not set
        RAILWAY_TOKEN: Railway API token (required for railway provider)
        RAILWAY_PROJECT_ID: Railway project ID (optional, auto-created if not set)

    Args:
        auth_type_override: Override auth type from CLI (takes precedence over env)
        provider_override: Override provider from CLI (takes precedence over env)

    Returns:
        QuickDeployConfig instance

    Raises:
        ConfigError: If required configuration is missing
    """
    # Determine provider: CLI override > env var > default
    provider_str = provider_override or os.environ.get("QUICKDEPLOY_PROVIDER", "gcp")
    try:
        provider = ProviderType(provider_str.lower())
    except ValueError:
        raise ConfigError(
            f"Invalid provider: {provider_str}. Must be 'gcp' or 'railway'."
        )

    # Get GCP-specific settings
    project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    zone = os.environ.get("QUICKDEPLOY_ZONE", "us-central1-a")
    bucket = os.environ.get("QUICKDEPLOY_BUCKET")
    machine_type = os.environ.get("QUICKDEPLOY_MACHINE_TYPE", "e2-medium")

    # Get Railway-specific settings
    railway_token = os.environ.get("RAILWAY_TOKEN")
    railway_project_id = os.environ.get("RAILWAY_PROJECT_ID")

    # Validate required fields based on provider
    if provider == ProviderType.GCP and not project:
        raise ConfigError(
            "GCP project not configured. Set QUICKDEPLOY_PROJECT or GOOGLE_CLOUD_PROJECT environment variable."
        )
    if provider == ProviderType.RAILWAY and not railway_token:
        raise ConfigError(
            "Railway token not configured. Set RAILWAY_TOKEN environment variable."
        )

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
        provider=provider,
        railway_token=railway_token,
        railway_project_id=railway_project_id,
    )

    if bucket:
        config.gcs_bucket = bucket

    return config
