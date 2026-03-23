"""
Root Typer CLI entry point for docto-trace-storage.

Registers sub-commands and exposes the --version flag.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from docto_trace import __version__
from docto_trace.commands import report as report_cmd
from docto_trace.commands import scan as scan_cmd

app = typer.Typer(
    name="docto-trace",
    help=(
        "[bold cyan]Docto Trace — Storage[/bold cyan] 🔍\n\n"
        "Deep storage auditing for Google Drive.\n"
        "Maps digital chaos, surfaces insights, and prepares your organization for AI-readiness."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

# Register sub-commands.
app.command(name="scan")(scan_cmd.scan)
app.command(name="report")(report_cmd.report)


@app.callback()
def main(
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
