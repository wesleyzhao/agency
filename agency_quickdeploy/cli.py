"""CLI for agency-quickdeploy.

This module provides the command-line interface for launching and managing
continuous Claude Code agents on GCP.
"""
import click
from rich.console import Console
from rich.table import Table

from agency_quickdeploy.config import load_config, ConfigError
from agency_quickdeploy.launcher import QuickDeployLauncher

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Agency QuickDeploy - Launch Claude Code agents on GCP with one command."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--name", "-n", help="Custom agent name (auto-generated if not provided)")
@click.option("--repo", "-r", help="Git repository to clone")
@click.option("--branch", "-b", help="Git branch to use")
@click.option("--spot", is_flag=True, help="Use spot/preemptible instance (cheaper)")
@click.option("--max-iterations", "-m", type=int, default=0, help="Max iterations (0=unlimited)")
def launch(prompt, name, repo, branch, spot, max_iterations):
    """Launch a new agent with the given PROMPT.

    Example:
        agency-quickdeploy launch "Build a todo app with React"
    """
    try:
        config = load_config()
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("\nSet QUICKDEPLOY_PROJECT environment variable to your GCP project ID.")
        raise SystemExit(1)

    console.print(f"[cyan]Launching agent...[/cyan]")
    console.print(f"  Project: {config.gcp_project}")
    console.print(f"  Zone: {config.gcp_zone}")
    console.print(f"  Bucket: {config.gcs_bucket}")

    launcher = QuickDeployLauncher(config)
    result = launcher.launch(
        prompt=prompt,
        name=name,
        repo=repo,
        branch=branch,
        spot=spot,
        max_iterations=max_iterations,
    )

    if result.error:
        console.print(f"\n[red]Launch failed:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"\n[green]Agent launched successfully![/green]")
    console.print(f"  Agent ID: {result.agent_id}")
    console.print(f"  Status: {result.status}")
    console.print(f"\nMonitor progress:")
    console.print(f"  agency-quickdeploy status {result.agent_id}")
    console.print(f"  agency-quickdeploy logs {result.agent_id}")


@cli.command()
@click.argument("agent_id")
def status(agent_id):
    """Get status of an agent.

    Example:
        agency-quickdeploy status agent-20260102-abc123
    """
    try:
        config = load_config()
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    agent_status = launcher.status(agent_id)

    console.print(f"\n[cyan]Agent Status: {agent_id}[/cyan]")
    console.print(f"  Status: {agent_status.get('status', 'unknown')}")

    if agent_status.get("vm_status"):
        console.print(f"  VM Status: {agent_status['vm_status']}")

    if agent_status.get("external_ip"):
        console.print(f"  External IP: {agent_status['external_ip']}")

    if agent_status.get("feature_count"):
        completed = agent_status.get("features_completed", 0)
        total = agent_status["feature_count"]
        console.print(f"  Progress: {completed}/{total} features completed")


@cli.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (not implemented)")
def logs(agent_id, follow):
    """Get logs for an agent.

    Example:
        agency-quickdeploy logs agent-20260102-abc123
    """
    try:
        config = load_config()
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
@click.confirmation_option(prompt="Are you sure you want to stop this agent?")
def stop(agent_id):
    """Stop and delete an agent.

    Example:
        agency-quickdeploy stop agent-20260102-abc123
    """
    try:
        config = load_config()
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
def list_agents():
    """List all quickdeploy agents.

    Example:
        agency-quickdeploy list
    """
    try:
        config = load_config()
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    agents = launcher.list_agents()

    if not agents:
        console.print("[yellow]No agents found[/yellow]")
        return

    table = Table(title="QuickDeploy Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("External IP")

    for agent in agents:
        table.add_row(
            agent.get("name", ""),
            agent.get("status", ""),
            agent.get("external_ip", ""),
        )

    console.print(table)


@cli.command()
def init():
    """Initialize quickdeploy (check configuration).

    Example:
        agency-quickdeploy init
    """
    console.print("[cyan]Checking configuration...[/cyan]")

    try:
        config = load_config()
        console.print(f"[green]Configuration valid![/green]")
        console.print(f"  Project: {config.gcp_project}")
        console.print(f"  Zone: {config.gcp_zone}")
        console.print(f"  Bucket: {config.gcs_bucket}")

        # Check if API key exists
        from agency_quickdeploy.gcp.secrets import SecretManager
        secrets = SecretManager(config.gcp_project)

        if secrets.exists(config.anthropic_api_key_secret):
            console.print(f"[green]API key found in Secret Manager[/green]")
        else:
            console.print(f"[yellow]Warning: API key not found in Secret Manager[/yellow]")
            console.print(f"  Create it with: gcloud secrets create {config.anthropic_api_key_secret} --data-file=<file>")

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("\nRequired environment variables:")
        console.print("  QUICKDEPLOY_PROJECT - GCP project ID")
        console.print("\nOptional environment variables:")
        console.print("  QUICKDEPLOY_ZONE - GCP zone (default: us-central1-a)")
        console.print("  QUICKDEPLOY_BUCKET - GCS bucket (auto-generated if not set)")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
