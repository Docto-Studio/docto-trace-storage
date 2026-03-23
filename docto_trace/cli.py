"""
Root Typer CLI entry point for docto-trace-storage.

Registers sub-commands and exposes the --version flag.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from docto_trace import __version__
from docto_trace.commands import login as login_cmd
from docto_trace.commands import logout as logout_cmd
from docto_trace.commands import report as report_cmd
from docto_trace.commands import scan as scan_cmd
from docto_trace.commands import setup as setup_cmd
from docto_trace.commands import ui as ui_cmd

app = typer.Typer(
    name="docto-trace",
    help=(
        "[bold cyan]Docto Trace — Storage[/bold cyan] 🔍\n\n"
        "Deep storage auditing for Google Drive.\n"
        "Maps digital chaos, surfaces insights, and prepares your organization for AI-readiness."
    ),
    rich_markup_mode="rich",
    no_args_is_help=False,       # Managed manually in the callback below.
    invoke_without_command=True, # Allows --version to fire without a subcommand.
    add_completion=True,
)

# Register sub-commands (in natural workflow order).
app.command(name="setup")(setup_cmd.setup)
app.command(name="login")(login_cmd.login)
app.command(name="logout")(logout_cmd.logout)
app.command(name="scan")(scan_cmd.scan)
app.command(name="report")(report_cmd.report)
app.command(name="ui")(ui_cmd.ui)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        is_eager=True,
        help="Show the installed version and exit.",
    ),
) -> None:
    """Docto Trace — Storage auditing CLI."""
    if version:
        rprint(f"[bold cyan]docto-trace-storage[/bold cyan] v[green]{__version__}[/green]")
        raise typer.Exit()
    # Show help when called with no subcommand and no flags.
    if ctx.invoked_subcommand is None:
        rprint(ctx.get_help())
        raise typer.Exit()
