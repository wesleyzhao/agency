"""Tell command - send instructions to running agent."""
import click
from rich.console import Console
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.argument("instruction", required=False)
@click.option("--file", "-f", "instruction_file", type=click.Path(exists=True), help="Read instruction from file")
def tell(agent_id, instruction, instruction_file):
    """Send an instruction to a running agent."""
    if instruction_file:
        with open(instruction_file) as f:
            instruction = f.read()

    if not instruction:
        console.print("[red]Error:[/red] Instruction required as argument or via --file")
        raise SystemExit(1)

    try:
        client = get_client()
        result = client.tell_agent(agent_id, instruction)
        client.close()
        console.print(f"[green]✓ Instruction sent to {agent_id}[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
