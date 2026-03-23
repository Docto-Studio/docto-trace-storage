"""
`docto-trace report` command — Phase 2 stub.

Provides a friendly placeholder and roadmap for the upcoming
Data Hygiene audit features (zombie detection, deduplication).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def report(
    report_json: Optional[Path] = typer.Argument(  # noqa: UP007
        None,
        help="Path to an existing report.json produced by 'docto-trace scan'.",
    ),
) -> None:
    """
    [Phase 2 — Coming in v0.2] Extended hygiene report.

    \b
    Will include:
      • 🧟 Zombie file detection (stale / orphaned files)
      • 🔍 Content fingerprinting & deduplication (MD5/SHA256)
      • 📋 Actionable remediation plan export

    Run 'docto-trace scan' first to generate a report.json.
    """
    console.print(
        Panel.fit(
            "[bold yellow]🚧 Phase 2 — Coming in v0.2[/bold yellow]\n\n"
            "The [cyan]report[/cyan] command will provide:\n"
            "  • [bold]Zombie file detection[/bold] — stale & orphaned files\n"
            "  • [bold]Deduplication[/bold] — MD5/SHA256 content fingerprinting\n"
            "  • [bold]Action Plan[/bold] — prioritized remediation suggestions\n\n"
            "In the meantime, run [green]docto-trace scan[/green] to get started.",
            title="Docto Trace — Report",
            border_style="yellow",
        )
    )
    raise typer.Exit(code=0)
