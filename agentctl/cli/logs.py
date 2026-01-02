"""Logs command - view agent output."""
import subprocess
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Stream logs continuously")
@click.option("--tail", "-n", default=100, help="Number of lines to show")
def logs(agent_id, follow, tail):
    """View agent logs."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    config = Config.load()
    instance_name = f"agent-{agent_id}"

    # Use gcloud to get serial console output (startup script logs)
    cmd = [
        "gcloud", "compute", "instances", "get-serial-port-output",
        instance_name,
        f"--zone={config.gcp_zone}",
        f"--project={config.gcp_project}",
    ]

    if follow:
        # For follow mode, SSH in and tail the log file
        ssh_cmd = [
            "gcloud", "compute", "ssh", instance_name,
            f"--zone={config.gcp_zone}",
            f"--project={config.gcp_project}",
            "--command", f"tail -f /var/log/syslog | grep -v CRON"
        ]
        subprocess.run(ssh_cmd)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines[-tail:]:
                console.print(line)
        else:
            console.print(f"[red]Error:[/red] {result.stderr}")
