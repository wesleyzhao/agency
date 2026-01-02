"""Logs command - view agent output."""
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError
from agentctl.shared.gcp import get_serial_port_output, GCPError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Stream logs continuously (requires SSH)")
@click.option("--tail", "-n", default=100, help="Number of lines to show")
def logs(agent_id, follow, tail):
    """View agent logs.

    Shows the VM's serial console output which includes startup script logs.
    Use --follow to stream logs in real-time via SSH.
    """
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    config = Config.load()
    instance_name = f"agent-{agent_id}"

    if follow:
        # For follow mode, we need SSH access
        # Try to use SSH if available
        import subprocess
        import shutil

        if shutil.which("ssh") and agent.get("external_ip"):
            # Direct SSH to tail logs
            ip = agent.get("external_ip")
            console.print(f"[dim]Connecting to {ip}...[/dim]")
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"root@{ip}",
                "tail -f /var/log/syslog 2>/dev/null || tail -f /workspace/agent.log 2>/dev/null || echo 'No logs found'"
            ]
            try:
                subprocess.run(ssh_cmd)
            except KeyboardInterrupt:
                pass
        elif shutil.which("gcloud"):
            # Fall back to gcloud compute ssh
            ssh_cmd = [
                "gcloud", "compute", "ssh", instance_name,
                f"--zone={config.gcp_zone}",
                f"--project={config.gcp_project}",
                "--command", "tail -f /var/log/syslog | grep -v CRON"
            ]
            try:
                subprocess.run(ssh_cmd)
            except KeyboardInterrupt:
                pass
        else:
            console.print("[yellow]Warning:[/yellow] --follow requires SSH access.")
            console.print("Install SSH or use: agentctl ssh {agent_id}")
            raise SystemExit(1)
    else:
        # Use Python SDK to get serial port output
        if not config.gcp_project:
            console.print("[red]Error:[/red] GCP not configured. Run 'agentctl init' first.")
            raise SystemExit(1)

        try:
            output = get_serial_port_output(
                project=config.gcp_project,
                zone=config.gcp_zone,
                instance=instance_name,
                service_account_file=config.service_account_file
            )
            lines = output.strip().split("\n")
            for line in lines[-tail:]:
                console.print(line)
        except GCPError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
