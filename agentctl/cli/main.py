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
    from agentctl.cli.agents import list_agents, status, stop, delete
    from agentctl.cli.tell import tell
    from agentctl.cli.init_cmd import init
    from agentctl.cli.ssh import ssh
    from agentctl.cli.logs import logs

    cli.add_command(init)
    cli.add_command(run)
    cli.add_command(list_agents)
    cli.add_command(status)
    cli.add_command(stop)
    cli.add_command(delete)
    cli.add_command(tell)
    cli.add_command(ssh)
    cli.add_command(logs)


register_commands()


if __name__ == "__main__":
    cli()
