"""Screenshots command - view agent screenshots."""
import click
from pathlib import Path
from rich.console import Console

from agentctl.shared.config import Config

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--download", "-d", is_flag=True, help="Download screenshots")
@click.option("--output", "-o", default="./screenshots", help="Download directory")
@click.option("--limit", "-n", default=10, help="Number of screenshots to list/download")
def screenshots(agent_id, download, output, limit):
    """List or download agent screenshots."""
    config = Config.load()

    if not config.gcs_bucket:
        console.print("[red]Error:[/red] Not initialized. Run 'agentctl init' first.")
        raise SystemExit(1)

    from agentctl.server.services.storage_manager import StorageManager
    storage = StorageManager(config.gcs_bucket)

    prefix = f"{agent_id}/screenshots/"
    files = storage.list_files(prefix)

    if not files:
        console.print("[dim]No screenshots found.[/dim]")
        return

    # Sort by name (timestamp) descending
    files = sorted(files, reverse=True)[:limit]

    if download:
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        for f in files:
            filename = f.split("/")[-1]
            local_path = output_path / filename
            storage.download_file(f, local_path)
            console.print(f"[green]✓[/green] Downloaded {filename}")

        console.print(f"\nScreenshots saved to {output_path}")
    else:
        console.print(f"[bold]Screenshots for {agent_id}:[/bold]\n")
        for f in files:
            filename = f.split("/")[-1]
            console.print(f"  {filename}")
        console.print(f"\nUse --download to save locally")
