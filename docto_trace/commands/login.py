"""`docto-trace login` command — authenticate with Google Drive explicitly."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from docto_trace.auth.google_drive import build_drive_service
from docto_trace.config import settings

console = Console()
err_console = Console(stderr=True)


def login(
    credentials: Path = typer.Option(
        settings.credentials_path,
        "--credentials",
        "-c",
        help="Path to the OAuth2 credentials JSON file.",
    ),
    service_account: Optional[Path] = typer.Option(  # noqa: UP007
        None,
        "--service-account",
        "-s",
        help="Path to a service account key JSON (skips OAuth2 browser flow).",
    ),
) -> None:
    """
    Authenticate with Google Drive and cache the token locally.

    Opens the browser OAuth2 consent flow (or reads a service-account key)
    and saves a ``token.json`` so subsequent commands run without prompting.

    \b
    Examples:
      docto-trace login
      docto-trace login --service-account ./sa-key.json
    """
    token_path = settings.token_path

    if token_path.exists():
        console.print(
            f"[yellow]⚠️  Already logged in.[/yellow] "
            f"Token cached at [dim]{token_path.resolve()}[/dim]"
        )
        console.print(
            "  Run [bold cyan]docto-trace logout[/bold cyan] first to switch accounts."
        )
        raise typer.Exit(code=0)

    try:
        err_console.print("[bold]🔐 Authenticating with Google Drive…[/bold]")
        build_drive_service(
            credentials_path=credentials,
            token_path=token_path,
            service_account_path=service_account,
        )
        console.print(
            f"[bold green]✅ Logged in.[/bold green] "
            f"Token cached at [dim]{token_path.resolve()}[/dim]"
        )
        console.print(
            "  Run [bold cyan]docto-trace scan[/bold cyan] to start auditing your Drive."
        )
    except FileNotFoundError as exc:
        err_console.print(f"\n[bold red]❌ Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        err_console.print(f"\n[bold red]❌ Unexpected error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
