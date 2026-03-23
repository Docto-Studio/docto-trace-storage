"""
`docto-trace ui` command.

Launches a local Streamlit web application to visually explore 
the given Docto Trace report.json.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()

def ui(
    report_json: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the report.json produced by 'docto-trace scan'."
    ),
) -> None:
    """
    [beta] Launch the interactive Streamlit UI for a report.

    Requires the optional 'ui' dependencies. If not installed, run:
        pip install "docto-trace-storage[ui]"
    """
    try:
        import streamlit  # noqa: F401
    except ImportError:
        console.print(
            Panel(
                "[bold red]Streamlit is not installed.[/bold red]\n\n"
                "The UI feature requires additional dependencies.\n"
                "Please install them by running:\n\n"
                "    [cyan]pip install \"docto-trace-storage\\[ui]\"[/cyan]",
                title="Missing Dependencies",
                border_style="red"
            )
        )
        raise typer.Exit(code=1)

    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    if not app_path.exists():
        console.print(f"[bold red]Error:[/bold red] Streamlit app not found at {app_path}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Launching Streamlit UI for {report_json}...[/bold green]")
    
    # We pass the absolute path of the report as a positional argument 
    # to the streamline script using '--'
    env = os.environ.copy()
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--", str(report_json.absolute())],
        env=env,
        check=False
    )
    raise typer.Exit(code=0)
