"""Run command - create and start an agent."""
import click
from rich.console import Console
from rich.table import Table

from agentctl.shared.config import Config, parse_duration
from agentctl.shared.api_client import get_client, APIError
from agentctl.shared.models import AgentConfig, EngineType

console = Console()


@click.command()
@click.argument("prompt", required=False)
@click.option("--name", "-n", help="Agent name (auto-generated if not provided)")
@click.option("--engine", "-e", type=click.Choice(["claude", "codex"]), default="claude", help="AI engine")
@click.option("--repo", "-r", help="Git repository URL to clone")
@click.option("--branch", "-b", help="Git branch to create/checkout")
@click.option("--timeout", "-t", default="4h", help="Auto-stop after duration (e.g., 4h, 30m)")
@click.option("--machine", "-m", default="e2-medium", help="GCE machine type")
@click.option("--spot", is_flag=True, help="Use spot/preemptible instance")
@click.option("--prompt-file", "-f", type=click.Path(exists=True), help="Read prompt from file")
@click.option("--screenshot-interval", type=int, default=300, help="Seconds between screenshots (0 to disable)")
@click.option("--screenshot-retention", default="24h", help="How long to keep screenshots")
def run(prompt, name, engine, repo, branch, timeout, machine, spot, prompt_file, screenshot_interval, screenshot_retention):
    """Start a new agent with the given PROMPT."""
    # Get prompt from file if specified
    if prompt_file:
        with open(prompt_file) as f:
            prompt = f.read()

    if not prompt:
        console.print("[red]Error:[/red] Prompt is required. Provide as argument or use --prompt-file")
        raise SystemExit(1)

    # Build config
    config = AgentConfig(
        prompt=prompt,
        name=name,
        engine=EngineType(engine),
        repo=repo,
        branch=branch,
        timeout_seconds=parse_duration(timeout),
        machine_type=machine,
        spot=spot,
        screenshot_interval=screenshot_interval,
        screenshot_retention=screenshot_retention,
    )

    # Call API
    try:
        client = get_client()
        console.print("[yellow]Creating agent...[/yellow]")
        result = client.create_agent(config)
        client.close()

        agent_id = result.get("id", "unknown")
        console.print(f"\n[green]✓ Agent created:[/green] {agent_id}")
        console.print(f"\n[dim]Monitor with:[/dim]")
        console.print(f"  agentctl logs {agent_id} --follow")
        console.print(f"  agentctl status {agent_id}")
        console.print(f"  agentctl ssh {agent_id}")

    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
