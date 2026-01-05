"""CLI for agency-quickdeploy.

This module provides the command-line interface for launching and managing
continuous Claude Code agents on GCP or Railway.
"""
import click
from rich.console import Console
from rich.table import Table

from agency_quickdeploy.config import load_config, load_dotenv, ConfigError
from agency_quickdeploy.launcher import QuickDeployLauncher

console = Console()

# Load .env file if it exists (before any commands run)
load_dotenv()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Agency QuickDeploy - Launch Claude Code agents on GCP or Railway with one command."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--name", "-n", help="Custom agent name (auto-generated if not provided)")
@click.option("--repo", "-r", help="Git repository to clone")
@click.option("--branch", "-b", help="Git branch to use")
@click.option("--spot", is_flag=True, help="Use spot/preemptible instance (cheaper, GCP only)")
@click.option("--max-iterations", "-m", type=int, default=0, help="Max iterations (0=unlimited)")
@click.option("--no-shutdown", is_flag=True, help="Keep running after completion (for inspection)")
@click.option(
    "--auth-type", "-a",
    type=click.Choice(["api_key", "oauth"], case_sensitive=False),
    help="Authentication type: api_key (default) or oauth (subscription-based)"
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Deployment provider: gcp (default) or railway"
)
def launch(prompt, name, repo, branch, spot, max_iterations, no_shutdown, auth_type, provider):
    """Launch a new agent with the given PROMPT.

    Example:
        agency-quickdeploy launch "Build a todo app with React"
        agency-quickdeploy launch "Build an API" --provider railway
        agency-quickdeploy launch "Build an API" --auth-type oauth
    """
    try:
        config = load_config(auth_type_override=auth_type, provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        if provider == "railway":
            console.print("\nSet RAILWAY_TOKEN environment variable.")
        else:
            console.print("\nSet QUICKDEPLOY_PROJECT environment variable to your GCP project ID.")
        raise SystemExit(1)

    console.print(f"[cyan]Launching agent...[/cyan]")
    console.print(f"  Provider: {config.provider.value}")
    if config.provider.value == "gcp":
        console.print(f"  Project: {config.gcp_project}")
        console.print(f"  Zone: {config.gcp_zone}")
        console.print(f"  Bucket: {config.gcs_bucket}")
    console.print(f"  Auth: {config.auth_type.value}")

    launcher = QuickDeployLauncher(config)
    result = launcher.launch(
        prompt=prompt,
        name=name,
        repo=repo,
        branch=branch,
        spot=spot,
        max_iterations=max_iterations,
        no_shutdown=no_shutdown,
    )

    if result.error:
        console.print(f"\n[red]Launch failed:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"\n[green]Agent launched successfully![/green]")
    console.print(f"  Agent ID: {result.agent_id}")
    console.print(f"  Status: {result.status}")
    if no_shutdown:
        console.print(f"  [yellow]NO_SHUTDOWN mode:[/yellow] Will stay running after completion")
    console.print(f"\nMonitor progress:")
    console.print(f"  agency-quickdeploy status {result.agent_id}")
    console.print(f"  agency-quickdeploy logs {result.agent_id}")
    if no_shutdown and config.provider.value == "gcp":
        console.print(f"\nSSH into VM:")
        console.print(f"  gcloud compute ssh {result.agent_id} --zone={config.gcp_zone} --project={config.gcp_project}")
    console.print(f"\nStop when done:")
    console.print(f"  agency-quickdeploy stop {result.agent_id}")


@cli.command()
@click.argument("agent_id")
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Deployment provider to query"
)
def status(agent_id, provider):
    """Get status of an agent.

    Example:
        agency-quickdeploy status agent-20260102-abc123
        agency-quickdeploy status agent-123 --provider railway
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    agent_status = launcher.status(agent_id)

    console.print(f"\n[cyan]Agent Status: {agent_id}[/cyan]")
    console.print(f"  Provider: {config.provider.value}")
    console.print(f"  Status: {agent_status.get('status', 'unknown')}")

    # GCP-specific info
    if agent_status.get("vm_status"):
        console.print(f"  VM Status: {agent_status['vm_status']}")

    if agent_status.get("external_ip"):
        console.print(f"  External IP: {agent_status['external_ip']}")

    # Railway-specific info
    if agent_status.get("railway_status"):
        console.print(f"  Railway Status: {agent_status['railway_status']}")

    if agent_status.get("url"):
        console.print(f"  URL: {agent_status['url']}")

    if agent_status.get("deployment_id"):
        console.print(f"  Deployment ID: {agent_status['deployment_id']}")

    # Progress info (GCP)
    if agent_status.get("feature_count"):
        completed = agent_status.get("features_completed", 0)
        total = agent_status["feature_count"]
        console.print(f"  Progress: {completed}/{total} features completed")


@cli.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (not implemented)")
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Deployment provider to query"
)
def logs(agent_id, follow, provider):
    """Get logs for an agent.

    Example:
        agency-quickdeploy logs agent-20260102-abc123
        agency-quickdeploy logs agent-123 --provider railway
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    log_content = launcher.logs(agent_id)

    if log_content:
        console.print(log_content)
    else:
        console.print(f"[yellow]No logs found for agent {agent_id}[/yellow]")


@cli.command()
@click.argument("agent_id")
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Deployment provider"
)
@click.confirmation_option(prompt="Are you sure you want to stop this agent?")
def stop(agent_id, provider):
    """Stop and delete an agent.

    Example:
        agency-quickdeploy stop agent-20260102-abc123
        agency-quickdeploy stop agent-123 --provider railway
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    success = launcher.stop(agent_id)

    if success:
        console.print(f"[green]Agent {agent_id} stopped successfully[/green]")
    else:
        console.print(f"[red]Failed to stop agent {agent_id}[/red]")
        raise SystemExit(1)


@cli.command("list")
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Deployment provider to list"
)
def list_agents(provider):
    """List all quickdeploy agents.

    Example:
        agency-quickdeploy list
        agency-quickdeploy list --provider railway
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    agents = launcher.list_agents()

    if not agents:
        console.print(f"[yellow]No agents found ({config.provider.value})[/yellow]")
        return

    table = Table(title=f"QuickDeploy Agents ({config.provider.value})")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")

    # Show URL for Railway, External IP for GCP
    if config.provider.value == "railway":
        table.add_column("URL")
        for agent in agents:
            table.add_row(
                agent.get("name", ""),
                agent.get("status", ""),
                agent.get("url", ""),
            )
    else:
        table.add_column("External IP")
        for agent in agents:
            table.add_row(
                agent.get("name", ""),
                agent.get("status", ""),
                agent.get("external_ip", ""),
            )

    console.print(table)


@cli.command()
@click.option(
    "--provider", "-p",
    type=click.Choice(["gcp", "railway"], case_sensitive=False),
    help="Check configuration for specific provider"
)
def init(provider):
    """Initialize quickdeploy (check configuration).

    Example:
        agency-quickdeploy init
        agency-quickdeploy init --provider railway
    """
    console.print("[cyan]Checking configuration...[/cyan]")

    try:
        config = load_config(provider_override=provider)
        console.print(f"[green]Configuration valid![/green]")
        console.print(f"  Provider: {config.provider.value}")

        if config.provider.value == "gcp":
            console.print(f"  Project: {config.gcp_project}")
            console.print(f"  Zone: {config.gcp_zone}")
            console.print(f"  Bucket: {config.gcs_bucket}")

            # Check if API key exists in Secret Manager
            from agency_quickdeploy.gcp.secrets import SecretManager
            secrets = SecretManager(config.gcp_project)

            if secrets.exists(config.anthropic_api_key_secret):
                console.print(f"[green]API key found in Secret Manager[/green]")
            else:
                console.print(f"[yellow]Warning: API key not found in Secret Manager[/yellow]")
                console.print(f"  Create it with: gcloud secrets create {config.anthropic_api_key_secret} --data-file=<file>")
        else:
            # Railway - validate token and test connectivity
            from agency_quickdeploy.providers.railway import (
                validate_railway_token_format,
                validate_railway_token_api,
            )

            console.print(f"  Token: {'set' if config.railway_token else 'not set'}")
            console.print(f"  Project ID: {config.railway_project_id or 'auto-create'}")

            # Validate token format
            if not validate_railway_token_format(config.railway_token):
                console.print(f"\n[red]Token format invalid![/red]")
                console.print("  Railway tokens should be UUIDs (e.g., 3fca9fef-8953-486f-b772-af5f34417ef7)")
                console.print("  Get a valid token at: railway.com/account/tokens")
                raise SystemExit(1)

            console.print(f"  Token format: [green]valid[/green]")

            # Test API connectivity
            console.print("\n[cyan]Testing API connectivity...[/cyan]")
            success, error = validate_railway_token_api(config.railway_token)

            if not success:
                console.print(f"[red]API connection failed:[/red] {error}")
                raise SystemExit(1)

            console.print(f"[green]Connected to Railway API![/green]")
            if config.railway_project_id:
                console.print(f"  Using project: {config.railway_project_id}")
            else:
                console.print("  Project: Will be created on first launch")

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        if provider == "railway":
            console.print("\nRequired for Railway:")
            console.print("  RAILWAY_TOKEN - Railway API token (get from railway.com/account/tokens)")
            console.print("\nOptional:")
            console.print("  RAILWAY_PROJECT_ID - Use existing project (creates new if not set)")
        else:
            console.print("\nRequired for GCP:")
            console.print("  QUICKDEPLOY_PROJECT - GCP project ID")
            console.print("\nOptional:")
            console.print("  QUICKDEPLOY_ZONE - GCP zone (default: us-central1-a)")
            console.print("  QUICKDEPLOY_BUCKET - GCS bucket (auto-generated if not set)")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
