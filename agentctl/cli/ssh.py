"""SSH command - connect to agent VM."""
import subprocess
import shutil
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--command", "-c", "remote_cmd", help="Command to run instead of interactive shell")
def ssh(agent_id, remote_cmd):
    """SSH into an agent's VM.

    Uses direct SSH if the VM has an external IP and SSH is available.
    Falls back to gcloud compute ssh if installed.
    """
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    external_ip = agent.get("external_ip")
    config = Config.load()
    instance_name = f"agent-{agent_id}"

    # Try direct SSH first if we have an IP
    if external_ip and shutil.which("ssh"):
        console.print(f"[dim]Connecting to {external_ip}...[/dim]")
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"root@{external_ip}"
        ]
        if remote_cmd:
            cmd.extend([remote_cmd])

        subprocess.run(cmd)
        return

    # Fall back to gcloud compute ssh
    if shutil.which("gcloud"):
        if not config.gcp_project:
            console.print("[red]Error:[/red] GCP not configured. Run 'agentctl init' first.")
            raise SystemExit(1)

        cmd = [
            "gcloud", "compute", "ssh", instance_name,
            f"--zone={config.gcp_zone}",
            f"--project={config.gcp_project}",
        ]
        if remote_cmd:
            cmd.extend(["--command", remote_cmd])

        subprocess.run(cmd)
        return

    # No SSH available
    if not external_ip:
        console.print(f"[red]Error:[/red] Agent {agent_id} has no external IP yet.")
        console.print("The VM may still be starting. Try again in a minute.")
    else:
        console.print(f"[red]Error:[/red] No SSH client available.")
        console.print(f"\nTo connect manually:")
        console.print(f"  ssh root@{external_ip}")
    raise SystemExit(1)
