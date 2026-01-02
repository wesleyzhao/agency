"""SSH command - connect to agent VM."""
import subprocess
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--command", "-c", "remote_cmd", help="Command to run instead of interactive shell")
def ssh(agent_id, remote_cmd):
    """SSH into an agent's VM."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    if not agent.get("external_ip"):
        console.print(f"[red]Error:[/red] Agent {agent_id} has no external IP")
        raise SystemExit(1)

    config = Config.load()
    instance_name = f"agent-{agent_id}"

    cmd = [
        "gcloud", "compute", "ssh", instance_name,
        f"--zone={config.gcp_zone}",
        f"--project={config.gcp_project}",
    ]

    if remote_cmd:
        cmd.extend(["--command", remote_cmd])

    # Execute SSH
    subprocess.run(cmd)
