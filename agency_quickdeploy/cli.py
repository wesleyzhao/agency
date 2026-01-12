"""CLI for agency-quickdeploy.

This module provides the command-line interface for launching and managing
continuous Claude Code agents on GCP, AWS, Railway, or locally via Docker.
"""
import click
from rich.console import Console
from rich.table import Table

from agency_quickdeploy.config import load_config, load_dotenv, ConfigError
from agency_quickdeploy.launcher import QuickDeployLauncher

# Import DockerError if available
try:
    from agency_quickdeploy.providers.docker import DockerError
except ImportError:
    DockerError = Exception  # Fallback if docker module not available

console = Console()

# Load .env file if it exists (before any commands run)
load_dotenv()


# Supported providers
PROVIDERS = ["gcp", "railway", "aws", "docker"]


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Agency QuickDeploy - Launch Claude Code agents on GCP, AWS, Railway, or Docker."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--name", "-n", help="Custom agent name (auto-generated if not provided)")
@click.option("--repo", "-r", help="Git repository to clone")
@click.option("--branch", "-b", help="Git branch to use")
@click.option("--spot", is_flag=True, help="Use spot/preemptible instance (cheaper, GCP only)")
@click.option("--max-iterations", "-m", type=int, default=0, help="Max iterations (0=unlimited)")
@click.option("--shutdown/--no-shutdown", default=False, help="Auto-shutdown VM on completion (default: keep running)")
@click.option(
    "--auth-type", "-a",
    type=click.Choice(["api_key", "oauth"], case_sensitive=False),
    help="Authentication type: api_key (default) or oauth (subscription-based)"
)
@click.option(
    "--provider", "-p",
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Deployment provider: gcp (default), aws, railway, or docker"
)
def launch(prompt, name, repo, branch, spot, max_iterations, shutdown, auth_type, provider):
    """Launch a new agent with the given PROMPT.

    Example:
        agency-quickdeploy launch "Build a todo app with React"
        agency-quickdeploy launch "Build an API" --provider aws
        agency-quickdeploy launch "Build an API" --provider docker
        agency-quickdeploy launch "Build an API" --auth-type oauth
        agency-quickdeploy launch "Build an API" --shutdown  # auto-shutdown on completion
    """
    try:
        config = load_config(auth_type_override=auth_type, provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        if provider == "railway":
            console.print("\nSet RAILWAY_TOKEN environment variable.")
        elif provider == "docker":
            console.print("\nDocker provider requires Docker to be installed and running.")
        elif provider == "aws":
            console.print("\nConfigure AWS credentials: aws configure")
        else:
            console.print("\nSet QUICKDEPLOY_PROJECT environment variable to your GCP project ID.")
        raise SystemExit(1)

    # Invert: shutdown=False means no_shutdown=True
    no_shutdown = not shutdown

    console.print(f"[cyan]Launching agent...[/cyan]")
    console.print(f"  Provider: {config.provider.value}")
    if config.provider.value == "gcp":
        console.print(f"  Project: {config.gcp_project}")
        console.print(f"  Zone: {config.gcp_zone}")
        console.print(f"  Bucket: {config.gcs_bucket}")
    elif config.provider.value == "aws":
        console.print(f"  Region: {config.aws_region}")
        if config.aws_bucket:
            console.print(f"  Bucket: {config.aws_bucket}")
        # Security note for AWS
        console.print(f"  [yellow]Note:[/yellow] Credentials passed via EC2 user-data")
    elif config.provider.value == "docker":
        console.print(f"  Image: {config.docker_image}")
        console.print(f"  Data dir: {config.docker_data_dir or '~/.agency'}")
    console.print(f"  Auth: {config.auth_type.value}")
    if shutdown:
        console.print(f"  [yellow]Auto-shutdown:[/yellow] VM will shutdown on completion")
    else:
        console.print(f"  [green]No auto-shutdown:[/green] VM stays running after completion")

    launcher = QuickDeployLauncher(config)
    try:
        result = launcher.launch(
            prompt=prompt,
            name=name,
            repo=repo,
            branch=branch,
            spot=spot,
            max_iterations=max_iterations,
            no_shutdown=no_shutdown,
        )
    except DockerError as e:
        console.print(f"\n[red]Docker error:[/red]\n{e.message}")
        raise SystemExit(1)

    if result.error:
        console.print(f"\n[red]Launch failed:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"\n[green]Agent launched successfully![/green]")
    console.print(f"  Agent ID: {result.agent_id}")
    console.print(f"  Status: {result.status}")
    console.print(f"\nMonitor progress:")
    console.print(f"  agency-quickdeploy status {result.agent_id}")
    console.print(f"  agency-quickdeploy logs {result.agent_id}")
    if not shutdown:
        if config.provider.value == "gcp":
            console.print(f"\nSSH into VM:")
            console.print(f"  gcloud compute ssh {result.agent_id} --zone={config.gcp_zone} --project={config.gcp_project}")
        elif config.provider.value == "docker":
            console.print(f"\nConnect to container:")
            console.print(f"  docker exec -it {result.agent_id} bash")
        elif config.provider.value == "aws":
            console.print(f"\nSSH into instance (get IP with status command):")
            console.print(f"  ssh -i ~/.agency/keys/{result.agent_id}.pem ubuntu@<external_ip>")
    console.print(f"\nStop when done:")
    console.print(f"  agency-quickdeploy stop {result.agent_id}")


@cli.command()
@click.argument("agent_id")
@click.option(
    "--provider", "-p",
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Deployment provider to query"
)
def status(agent_id, provider):
    """Get status of an agent.

    Example:
        agency-quickdeploy status agent-20260102-abc123
        agency-quickdeploy status agent-123 --provider docker
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    try:
        agent_status = launcher.status(agent_id)
    except DockerError as e:
        console.print(f"\n[red]Docker error:[/red]\n{e.message}")
        raise SystemExit(1)

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

    # Docker-specific info
    if agent_status.get("docker_status"):
        console.print(f"  Docker Status: {agent_status['docker_status']}")

    if agent_status.get("container_id"):
        console.print(f"  Container ID: {agent_status['container_id']}")

    if agent_status.get("logs_command"):
        console.print(f"  View logs: {agent_status['logs_command']}")

    if agent_status.get("ssh_command"):
        console.print(f"  Connect: {agent_status['ssh_command']}")

    # AWS-specific info
    if agent_status.get("instance_id"):
        console.print(f"  Instance ID: {agent_status['instance_id']}")

    # Progress info
    if agent_status.get("feature_count"):
        completed = agent_status.get("features_completed", 0)
        total = agent_status["feature_count"]
        console.print(f"  Progress: {completed}/{total} features completed")
    elif agent_status.get("features"):
        console.print(f"  Progress: {agent_status['features']}")


@cli.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (not implemented)")
@click.option(
    "--provider", "-p",
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Deployment provider to query"
)
def logs(agent_id, follow, provider):
    """Get logs for an agent.

    Example:
        agency-quickdeploy logs agent-20260102-abc123
        agency-quickdeploy logs agent-123 --provider docker
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    try:
        log_content = launcher.logs(agent_id)
    except DockerError as e:
        console.print(f"\n[red]Docker error:[/red]\n{e.message}")
        raise SystemExit(1)

    if log_content:
        console.print(log_content)
    else:
        console.print(f"[yellow]No logs found for agent {agent_id}[/yellow]")


@cli.command()
@click.argument("agent_id")
@click.option(
    "--provider", "-p",
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Deployment provider"
)
@click.confirmation_option(prompt="Are you sure you want to stop this agent?")
def stop(agent_id, provider):
    """Stop and delete an agent.

    Example:
        agency-quickdeploy stop agent-20260102-abc123
        agency-quickdeploy stop agent-123 --provider docker
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    try:
        success = launcher.stop(agent_id)
    except DockerError as e:
        console.print(f"\n[red]Docker error:[/red]\n{e.message}")
        raise SystemExit(1)

    if success:
        console.print(f"[green]Agent {agent_id} stopped successfully[/green]")
    else:
        console.print(f"[red]Failed to stop agent {agent_id}[/red]")
        raise SystemExit(1)


@cli.command("list")
@click.option(
    "--provider", "-p",
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Deployment provider to list"
)
def list_agents(provider):
    """List all quickdeploy agents.

    Example:
        agency-quickdeploy list
        agency-quickdeploy list --provider docker
    """
    try:
        config = load_config(provider_override=provider)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1)

    launcher = QuickDeployLauncher(config)
    try:
        agents = launcher.list_agents()
    except DockerError as e:
        console.print(f"\n[red]Docker error:[/red]\n{e.message}")
        raise SystemExit(1)

    if not agents:
        console.print(f"[yellow]No agents found ({config.provider.value})[/yellow]")
        return

    table = Table(title=f"QuickDeploy Agents ({config.provider.value})")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")

    # Show different info based on provider
    if config.provider.value == "railway":
        table.add_column("URL")
        for agent in agents:
            table.add_row(
                agent.get("name", ""),
                agent.get("status", ""),
                agent.get("url", ""),
            )
    elif config.provider.value == "docker":
        table.add_column("Container ID")
        for agent in agents:
            table.add_row(
                agent.get("name", ""),
                agent.get("status", ""),
                agent.get("container_id", ""),
            )
    elif config.provider.value == "aws":
        table.add_column("Instance ID")
        table.add_column("External IP")
        for agent in agents:
            table.add_row(
                agent.get("name", ""),
                agent.get("status", ""),
                agent.get("instance_id", ""),
                agent.get("external_ip", ""),
            )
    else:  # gcp
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
    type=click.Choice(PROVIDERS, case_sensitive=False),
    help="Check configuration for specific provider"
)
def init(provider):
    """Initialize quickdeploy (check configuration).

    Example:
        agency-quickdeploy init
        agency-quickdeploy init --provider docker
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

        elif config.provider.value == "railway":
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

        elif config.provider.value == "docker":
            # Docker - check Docker daemon and pull image
            console.print(f"  Image: {config.docker_image}")
            console.print(f"  Data dir: {config.docker_data_dir or '~/.agency'}")

            console.print("\n[cyan]Checking Docker daemon...[/cyan]")
            try:
                from agency_quickdeploy.providers.docker import DockerProvider
                docker_provider = DockerProvider(config)
                docker_provider.docker  # Test connection
                console.print(f"[green]Docker daemon is running![/green]")

                # Try to pull the image
                console.print(f"\n[cyan]Pulling agent image: {config.docker_image}...[/cyan]")
                if docker_provider.pull_image():
                    console.print(f"[green]Image ready![/green]")
                else:
                    console.print(f"[yellow]Could not pull image - will try again on launch[/yellow]")

            except Exception as e:
                console.print(f"[red]Docker error:[/red] {e}")
                raise SystemExit(1)

            # Check for credentials
            import os
            if os.environ.get("ANTHROPIC_API_KEY"):
                console.print(f"[green]API key found in environment[/green]")
            elif os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
                console.print(f"[green]OAuth token found in environment[/green]")
            else:
                console.print(f"[yellow]Warning: No credentials found[/yellow]")
                console.print("  Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN environment variable")

        elif config.provider.value == "aws":
            # AWS - check credentials and region
            console.print(f"  Region: {config.aws_region}")
            console.print(f"  Instance type: {config.aws_instance_type}")
            if config.aws_bucket:
                console.print(f"  Bucket: {config.aws_bucket}")
            else:
                console.print(f"  Bucket: auto-generated on launch")

            console.print("\n[cyan]Checking AWS credentials...[/cyan]")
            try:
                import boto3
                sts = boto3.client('sts', region_name=config.aws_region)
                identity = sts.get_caller_identity()
                console.print(f"[green]AWS credentials valid![/green]")
                console.print(f"  Account: {identity['Account']}")
                console.print(f"  User ARN: {identity['Arn']}")
            except Exception as e:
                console.print(f"[red]AWS error:[/red] {e}")
                console.print("\nConfigure AWS credentials with: aws configure")
                raise SystemExit(1)

            # Check for agent credentials
            import os
            if os.environ.get("ANTHROPIC_API_KEY"):
                console.print(f"[green]API key found in environment[/green]")
            elif os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
                console.print(f"[green]OAuth token found in environment[/green]")
            else:
                console.print(f"[yellow]Warning: No agent credentials found[/yellow]")
                console.print("  Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN environment variable")

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        if provider == "railway":
            console.print("\nRequired for Railway:")
            console.print("  RAILWAY_TOKEN - Railway API token (get from railway.com/account/tokens)")
            console.print("\nOptional:")
            console.print("  RAILWAY_PROJECT_ID - Use existing project (creates new if not set)")
        elif provider == "docker":
            console.print("\nRequired for Docker:")
            console.print("  Docker must be installed and running")
            console.print("\nOptional:")
            console.print("  AGENCY_DATA_DIR - Local data directory (default: ~/.agency)")
            console.print("  AGENCY_DOCKER_IMAGE - Custom Docker image")
        elif provider == "aws":
            console.print("\nRequired for AWS:")
            console.print("  AWS credentials (aws configure)")
            console.print("\nOptional:")
            console.print("  AWS_REGION - AWS region (default: us-east-1)")
            console.print("  AWS_BUCKET - S3 bucket for state (auto-generated if not set)")
        else:
            console.print("\nRequired for GCP:")
            console.print("  QUICKDEPLOY_PROJECT - GCP project ID")
            console.print("\nOptional:")
            console.print("  QUICKDEPLOY_ZONE - GCP zone (default: us-central1-a)")
            console.print("  QUICKDEPLOY_BUCKET - GCS bucket (auto-generated if not set)")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
