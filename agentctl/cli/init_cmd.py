"""Init command - set up GCP project."""
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from getpass import getpass
import secrets

from agentctl.shared.config import Config, CONFIG_DIR
from agentctl.shared.gcp import get_project_id, verify_auth, enable_api, GCPError

console = Console()


@click.command()
@click.option("--project", "-p", help="GCP project ID")
@click.option("--region", default="us-central1", help="GCP region")
@click.option("--zone", default="us-central1-a", help="GCP zone")
@click.option("--service-account", "-s", help="Path to service account JSON file")
def init(project, region, zone, service_account):
    """Initialize AgentCtl in a GCP project.

    Authentication can be done via:
    - Service account JSON file (--service-account or GOOGLE_APPLICATION_CREDENTIALS)
    - Application Default Credentials (gcloud auth application-default login)
    """

    console.print("\n[bold]Initializing AgentCtl[/bold]\n")

    # Step 1: Verify GCP auth
    if not verify_auth(service_account):
        console.print("[red]Error:[/red] GCP authentication failed.")
        console.print("\nTo authenticate, do one of:")
        console.print("  1. Use a service account: agentctl init --service-account /path/to/key.json")
        console.print("  2. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        console.print("  3. Run: gcloud auth application-default login")
        raise SystemExit(1)
    console.print("[green]✓[/green] GCP authentication verified")

    # Step 2: Get project
    if not project:
        project = get_project_id(service_account)
        if not project:
            project = click.prompt("GCP Project ID")
    console.print(f"[green]✓[/green] Using project: {project}")

    # Step 3: Enable APIs
    apis = [
        "compute.googleapis.com",
        "secretmanager.googleapis.com",
        "storage.googleapis.com",
        "serviceusage.googleapis.com",  # Needed for enabling other APIs
    ]
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Enabling APIs...", total=len(apis))
        for api in apis:
            try:
                enable_api(project, api, service_account)
            except GCPError as e:
                console.print(f"\n[yellow]Warning:[/yellow] {e}")
            progress.advance(task)
    console.print("[green]✓[/green] APIs enabled")

    # Step 4: Create GCS bucket
    bucket_name = f"agentctl-{project}-{secrets.token_hex(4)}"
    try:
        from agentctl.server.services.storage_manager import StorageManager
        storage = StorageManager(bucket_name)
        storage.create_bucket(location=region)
        console.print(f"[green]✓[/green] Created bucket: {bucket_name}")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not create bucket: {e}")
        bucket_name = click.prompt("Enter existing bucket name")

    # Step 5: Store API keys
    console.print("\n[bold]API Keys[/bold]")
    console.print("[dim]These will be stored in GCP Secret Manager[/dim]\n")

    from agentctl.server.services.secret_manager import SecretManagerService
    secrets_svc = SecretManagerService(project)

    anthropic_key = getpass("Anthropic API Key: ")
    if anthropic_key:
        secrets_svc.set_secret("anthropic-api-key", anthropic_key)
        console.print("[green]✓[/green] Anthropic key saved")

    github_token = getpass("GitHub Token (optional, press Enter to skip): ")
    if github_token:
        secrets_svc.set_secret("github-token", github_token)
        console.print("[green]✓[/green] GitHub token saved")

    # Step 6: Save config
    config = Config(
        gcp_project=project,
        gcp_region=region,
        gcp_zone=zone,
        gcs_bucket=bucket_name,
        service_account_file=service_account,
        master_server_url="http://localhost:8000",  # Default to local for now
    )
    config.save()
    console.print(f"[green]✓[/green] Config saved to {CONFIG_DIR / 'config.yaml'}")

    # Done
    console.print("\n[bold green]✓ AgentCtl initialized![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Start the server: uvicorn agentctl.server.app:app")
    console.print("  2. Run an agent: agentctl run 'Build something cool'")
