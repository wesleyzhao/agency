"""Agent management commands."""
import click
from rich.console import Console
from rich.table import Table

from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--format", "-o", "output_format", type=click.Choice(["table", "json"]), default="table")
def list_agents(status, output_format):
    """List all agents."""
    try:
        client = get_client()
        agents = client.list_agents(status=status)
        client.close()

        if output_format == "json":
            import json
            console.print(json.dumps(agents, indent=2))
            return

        if not agents:
            console.print("[dim]No agents found.[/dim]")
            return

        table = Table(title="Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Status")
        table.add_column("Engine")
        table.add_column("Created")
        table.add_column("IP")

        for agent in agents:
            status_style = {
                "running": "green",
                "stopped": "dim",
                "failed": "red",
                "starting": "yellow",
            }.get(agent.get("status", ""), "")

            table.add_row(
                agent.get("id", ""),
                f"[{status_style}]{agent.get('status', '')}[/{status_style}]",
                agent.get("engine", ""),
                agent.get("created_at", "")[:19] if agent.get("created_at") else "",
                agent.get("external_ip", "") or "-",
            )

        console.print(table)

    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
def status(agent_id):
    """Get detailed status of an agent."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()

        console.print(f"\n[bold]Agent:[/bold] {agent.get('id')}")
        console.print(f"[bold]Status:[/bold] {agent.get('status')}")
        console.print(f"[bold]Engine:[/bold] {agent.get('engine')}")
        console.print(f"[bold]Prompt:[/bold] {agent.get('prompt', '')[:100]}...")

        if agent.get("repo"):
            console.print(f"[bold]Repo:[/bold] {agent.get('repo')}")
        if agent.get("branch"):
            console.print(f"[bold]Branch:[/bold] {agent.get('branch')}")
        if agent.get("external_ip"):
            console.print(f"[bold]IP:[/bold] {agent.get('external_ip')}")

        console.print(f"[bold]Created:[/bold] {agent.get('created_at')}")
        if agent.get("started_at"):
            console.print(f"[bold]Started:[/bold] {agent.get('started_at')}")

    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def stop(agent_id, force):
    """Stop a running agent."""
    if not force:
        if not click.confirm(f"Stop agent {agent_id}?"):
            return

    try:
        client = get_client()
        result = client.stop_agent(agent_id)
        client.close()
        console.print(f"[green]✓ Agent {agent_id} stopped[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def delete(agent_id, force):
    """Delete an agent and its resources."""
    if not force:
        if not click.confirm(f"Delete agent {agent_id}? This cannot be undone."):
            return

    try:
        client = get_client()
        client.delete_agent(agent_id)
        client.close()
        console.print(f"[green]✓ Agent {agent_id} deleted[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
