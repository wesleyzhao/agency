"""GCP client utilities."""
import subprocess
from typing import Optional


class GCPError(Exception):
    """GCP operation failed."""
    pass


def get_project_id() -> Optional[str]:
    """Get current GCP project from gcloud config."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True
        )
        project = result.stdout.strip()
        return project if project else None
    except subprocess.CalledProcessError:
        return None


def verify_auth() -> bool:
    """Verify gcloud authentication."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def enable_api(project: str, api: str) -> None:
    """Enable a GCP API."""
    try:
        subprocess.run(
            ["gcloud", "services", "enable", api, f"--project={project}"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        raise GCPError(f"Failed to enable {api}: {e.stderr}")
