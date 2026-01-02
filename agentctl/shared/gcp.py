"""GCP client utilities - pure Python implementation."""
import os
from typing import Optional, Tuple

# Google auth libraries
try:
    import google.auth
    from google.auth import exceptions as auth_exceptions
    from google.oauth2 import service_account
    from googleapiclient import discovery
    from googleapiclient.errors import HttpError
    HAS_GCP_LIBS = True
except ImportError:
    HAS_GCP_LIBS = False


class GCPError(Exception):
    """GCP operation failed."""
    pass


def check_gcp_libs() -> None:
    """Verify GCP libraries are installed."""
    if not HAS_GCP_LIBS:
        raise GCPError(
            "GCP libraries not installed. Run: pip install google-auth google-api-python-client"
        )


def get_credentials(
    service_account_file: Optional[str] = None,
    scopes: Optional[list] = None
) -> Tuple:
    """Get GCP credentials.

    Tries in order:
    1. Service account file (if provided or GOOGLE_APPLICATION_CREDENTIALS env var)
    2. Application Default Credentials (ADC)

    Returns:
        Tuple of (credentials, project_id)
    """
    check_gcp_libs()

    default_scopes = scopes or ["https://www.googleapis.com/auth/cloud-platform"]

    # Try service account file first
    sa_file = service_account_file or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_file and os.path.exists(sa_file):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                sa_file, scopes=default_scopes
            )
            # Extract project from service account
            import json
            with open(sa_file) as f:
                sa_info = json.load(f)
            project_id = sa_info.get("project_id")
            return credentials, project_id
        except Exception as e:
            raise GCPError(f"Failed to load service account: {e}")

    # Fall back to Application Default Credentials
    try:
        credentials, project_id = google.auth.default(scopes=default_scopes)
        return credentials, project_id
    except auth_exceptions.DefaultCredentialsError:
        raise GCPError(
            "No GCP credentials found. Either:\n"
            "  1. Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file\n"
            "  2. Run 'gcloud auth application-default login'\n"
            "  3. Run on a GCP VM with a service account"
        )


def get_project_id(service_account_file: Optional[str] = None) -> Optional[str]:
    """Get GCP project ID from credentials."""
    try:
        _, project_id = get_credentials(service_account_file)
        return project_id
    except GCPError:
        return None


def verify_auth(service_account_file: Optional[str] = None) -> bool:
    """Verify GCP authentication is working."""
    try:
        credentials, _ = get_credentials(service_account_file)
        # Try to refresh credentials to verify they work
        if hasattr(credentials, 'refresh'):
            import google.auth.transport.requests
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
        return True
    except Exception:
        return False


def enable_api(project: str, api: str, service_account_file: Optional[str] = None) -> None:
    """Enable a GCP API using Python SDK."""
    check_gcp_libs()

    credentials, _ = get_credentials(service_account_file)

    try:
        service = discovery.build(
            "serviceusage", "v1",
            credentials=credentials,
            cache_discovery=False
        )

        # API name format: projects/{project}/services/{api}
        name = f"projects/{project}/services/{api}"

        # Check if already enabled
        try:
            result = service.services().get(name=name).execute()
            if result.get("state") == "ENABLED":
                return  # Already enabled
        except HttpError:
            pass  # Not enabled yet, continue to enable

        # Enable the API
        request = service.services().enable(name=name)
        operation = request.execute()

        # Wait for operation to complete (optional, APIs enable async)
        # For simplicity, we just fire and forget - the API will be ready soon

    except HttpError as e:
        raise GCPError(f"Failed to enable {api}: {e}")


def list_enabled_apis(project: str, service_account_file: Optional[str] = None) -> list:
    """List enabled APIs for a project."""
    check_gcp_libs()

    credentials, _ = get_credentials(service_account_file)

    try:
        service = discovery.build(
            "serviceusage", "v1",
            credentials=credentials,
            cache_discovery=False
        )

        parent = f"projects/{project}"
        request = service.services().list(parent=parent, filter="state:ENABLED")
        response = request.execute()

        services = response.get("services", [])
        return [s["config"]["name"] for s in services]

    except HttpError as e:
        raise GCPError(f"Failed to list APIs: {e}")


def get_serial_port_output(
    project: str,
    zone: str,
    instance: str,
    port: int = 1,
    service_account_file: Optional[str] = None
) -> str:
    """Get serial port output from a VM instance."""
    check_gcp_libs()

    credentials, _ = get_credentials(service_account_file)

    try:
        service = discovery.build(
            "compute", "v1",
            credentials=credentials,
            cache_discovery=False
        )

        request = service.instances().getSerialPortOutput(
            project=project,
            zone=zone,
            instance=instance,
            port=port
        )
        response = request.execute()

        return response.get("contents", "")

    except HttpError as e:
        raise GCPError(f"Failed to get serial output: {e}")
