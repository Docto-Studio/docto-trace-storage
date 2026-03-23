"""`docto-trace logout` command — revoke the cached OAuth2 token."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from docto_trace.config import settings

console = Console()
err_console = Console(stderr=True)


def logout(
    token_path: Optional[Path] = typer.Option(  # noqa: UP007
        None,
        "--token",
        "-t",
        help="Path to the cached token file. Defaults to the configured token path.",
    ),
    revoke: bool = typer.Option(
        False,
        "--revoke",
        "-R",
        help="Also revoke the token on Google's servers (requires network).",
    ),
) -> None:
    """
    Clear the cached Google Drive authentication token.

    Deletes the local token file so the next ``docto-trace scan`` will
    trigger a fresh browser OAuth2 login flow.

    \b
    Examples:
      docto-trace logout
      docto-trace logout --revoke          # also revokes on Google's servers
      docto-trace logout --token ./my.json
    """
    target = token_path or settings.token_path

    if not target.exists():
        console.print(
            f"[yellow]⚠️  No token found at [bold]{target}[/bold] — already logged out.[/yellow]"
        )
        raise typer.Exit(code=0)

    # Optionally revoke the token on Google's authorization server first.
    if revoke:
        _revoke_token(target)

    target.unlink()
    console.print(
        f"[bold green]✅ Logged out.[/bold green] "
        f"Token deleted: [dim]{target.resolve()}[/dim]"
    )
    console.print(
        "  Run [bold cyan]docto-trace scan[/bold cyan] again to re-authenticate."
    )


def _revoke_token(token_path: Path) -> None:
    """Send a revocation request to Google's OAuth2 endpoint."""
    import json

    import httplib2

    try:
        raw = json.loads(token_path.read_text(encoding="utf-8"))
        token = raw.get("token") or raw.get("access_token")
        if not token:
            console.print("[dim]No active access token to revoke.[/dim]")
            return

        http = httplib2.Http()
        resp, _ = http.request(
            f"https://oauth2.googleapis.com/revoke?token={token}",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status == 200:
            console.print("[green]🔒 Token revoked on Google's servers.[/green]")
        else:
            console.print(
                f"[yellow]⚠️  Revocation returned HTTP {resp.status}. "
                "Token may already be expired — continuing with local deletion.[/yellow]"
            )
    except Exception as exc:  # noqa: BLE001
        console.print(
            f"[yellow]⚠️  Could not revoke token remotely ({exc}). "
            "Local file will still be deleted.[/yellow]"
        )
