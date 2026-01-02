"""Configuration management."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


CONFIG_DIR = Path.home() / ".agentctl"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class Config:
    """Application configuration."""
    # GCP settings
    gcp_project: Optional[str] = None
    gcp_region: str = "us-central1"
    gcp_zone: str = "us-central1-a"
    service_account_file: Optional[str] = None  # Path to service account JSON

    # Server settings
    master_server_url: Optional[str] = None

    # Storage
    gcs_bucket: Optional[str] = None

    # Defaults
    default_machine_type: str = "e2-medium"
    default_timeout: str = "4h"
    default_engine: str = "claude"
    screenshot_interval: int = 300
    screenshot_retention: str = "24h"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """Load config from file, with env var overrides."""
        path = path or CONFIG_FILE
        config = cls()

        # Load from file if exists
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Environment variable overrides
        env_mappings = {
            "AGENTCTL_GCP_PROJECT": "gcp_project",
            "AGENTCTL_GCP_REGION": "gcp_region",
            "AGENTCTL_GCP_ZONE": "gcp_zone",
            "AGENTCTL_MASTER_URL": "master_server_url",
            "GOOGLE_APPLICATION_CREDENTIALS": "service_account_file",
        }
        for env_var, attr in env_mappings.items():
            if env_var in os.environ:
                setattr(config, attr, os.environ[env_var])

        return config

    def save(self, path: Optional[Path] = None) -> None:
        """Save config to file."""
        path = path or CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "gcp_project": self.gcp_project,
            "gcp_region": self.gcp_region,
            "gcp_zone": self.gcp_zone,
            "service_account_file": self.service_account_file,
            "master_server_url": self.master_server_url,
            "gcs_bucket": self.gcs_bucket,
            "default_machine_type": self.default_machine_type,
            "default_timeout": self.default_timeout,
            "default_engine": self.default_engine,
            "screenshot_interval": self.screenshot_interval,
            "screenshot_retention": self.screenshot_retention,
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.master_server_url:
            errors.append("master_server_url is required")
        return errors


def parse_duration(duration: str) -> int:
    """Parse duration string (e.g., '4h', '30m') to seconds."""
    duration = duration.strip().lower()
    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    elif duration.endswith("m"):
        return int(duration[:-1]) * 60
    elif duration.endswith("s"):
        return int(duration[:-1])
    else:
        return int(duration)
