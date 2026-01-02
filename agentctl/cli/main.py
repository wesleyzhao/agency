"""Main CLI entry point."""
import click
from rich.console import Console

console = Console()

# Version
VERSION = "0.1.0"


@click.group()
@click.version_option(version=VERSION)
@click.pass_context
def cli(ctx):
    """AgentCtl - Manage autonomous AI coding agents."""
    ctx.ensure_object(dict)


def register_commands():
    """Register all CLI commands."""
    from agentctl.cli.run import run
    cli.add_command(run)


register_commands()


if __name__ == "__main__":
    cli()
