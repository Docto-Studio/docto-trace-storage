"""`docto-trace setup` — guided wizard to create your own Google Cloud credentials."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()


def setup(
    output: Path = typer.Option(
        Path("credentials.json"),
        "--output",
        "-o",
        help="Where to save the downloaded credentials file.",
    ),
) -> None:
    """
    Interactive wizard to configure your own Google Cloud credentials.

    Walks you through creating a Google Cloud project, enabling the Drive API,
    and generating OAuth2 credentials — so your data never touches anyone
    else's app registration.

    \b
    Why use your own credentials?
      The Drive API is called entirely from YOUR machine. Your data never
      passes through Docto servers. But if you want full control over the
      OAuth2 consent screen and API quotas, set up your own project.

    \b
    Examples:
      docto-trace setup
      docto-trace setup --output ~/my-drive-creds.json
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]docto-trace setup[/bold cyan]\n"
            "[dim]Create your own Google Cloud credentials in ~5 minutes.[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # ------------------------------------------------------------------
    # Step 1 — Google Cloud project
    # ------------------------------------------------------------------
    console.rule("[bold]Step 1 of 4 — Create a Google Cloud project[/bold]")
    console.print(
        "\nDocto Trace needs a Google Cloud project to access the Drive API on your behalf.\n"
        "If you already have one, you can skip this step.\n"
    )
    if Confirm.ask("  Open Google Cloud Console in your browser?", default=True):
        webbrowser.open("https://console.cloud.google.com/projectcreate")
        console.print(
            "  1. Fill in a [bold]Project name[/bold] (e.g. [cyan]docto-trace[/cyan]).\n"
            "  2. Click [bold]Create[/bold] and wait for it to be ready.\n"
        )
    Prompt.ask("  Press [bold]Enter[/bold] when your project is selected in the console")

    # ------------------------------------------------------------------
    # Step 2 — Enable the Drive API
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 2 of 4 — Enable the Google Drive API[/bold]")
    console.print(
        "\nDocto Trace uses two [green]read-only[/green] scopes — it can never modify or delete files:\n"
        "  • [cyan]drive.readonly[/cyan]           — list and read file metadata\n"
        "  • [cyan]drive.metadata.readonly[/cyan]  — access checksums and modification times\n"
    )
    if Confirm.ask("  Open the Drive API enablement page?", default=True):
        webbrowser.open(
            "https://console.cloud.google.com/apis/library/drive.googleapis.com"
        )
        console.print("  Click [bold]Enable[/bold] if it is not already enabled.\n")
    Prompt.ask("  Press [bold]Enter[/bold] when the API is enabled")

    # ------------------------------------------------------------------
    # Step 3 — OAuth2 consent screen
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 3 of 4 — Configure the OAuth2 consent screen[/bold]")
    console.print(
        "\nGoogle requires a consent screen before issuing credentials.\n"
    )
    if Confirm.ask("  Open the OAuth consent screen page?", default=True):
        webbrowser.open(
            "https://console.cloud.google.com/apis/credentials/consent"
        )
        console.print(
            "  1. Select [bold]External[/bold] (or Internal if you use Google Workspace).\n"
            "  2. Fill in App name (e.g. [cyan]docto-trace[/cyan]) and your email.\n"
            "  3. Click [bold]Save and Continue[/bold] through all steps.\n"
            "  4. On the [bold]Test users[/bold] step, add your own Google account email.\n"
        )
    Prompt.ask("  Press [bold]Enter[/bold] when the consent screen is configured")

    # ------------------------------------------------------------------
    # Step 4 — Download credentials.json
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 4 of 4 — Create & download OAuth2 credentials[/bold]")
    console.print()
    if Confirm.ask("  Open the Credentials page?", default=True):
        webbrowser.open("https://console.cloud.google.com/apis/credentials")
        console.print(
            "  1. Click [bold]+ Create Credentials → OAuth client ID[/bold].\n"
            "  2. Select [bold]Desktop app[/bold] as the application type.\n"
            "  3. Click [bold]Create[/bold], then [bold]Download JSON[/bold].\n"
            f"  4. Save the file to: [bold cyan]{output.resolve()}[/bold cyan]\n"
        )
    Prompt.ask(f"  Press [bold]Enter[/bold] when you have saved the JSON to [cyan]{output}[/cyan]")

    # ------------------------------------------------------------------
    # Validate the downloaded file
    # ------------------------------------------------------------------
    console.print()
    if not output.exists():
        console.print(
            f"[bold red]❌ File not found:[/bold red] [dim]{output.resolve()}[/dim]\n"
            f"  Move your downloaded file to [bold]{output.resolve()}[/bold] and re-run setup."
        )
        raise typer.Exit(code=1)

    try:
        data = json.loads(output.read_text(encoding="utf-8"))
        client_id = (
            data.get("installed", data.get("web", {})).get("client_id", "—")
        )
        console.print(
            Panel.fit(
                f"[bold green]✅ Credentials validated![/bold green]\n\n"
                f"  File:      [dim]{output.resolve()}[/dim]\n"
                f"  Client ID: [dim]{client_id[:40]}…[/dim]\n\n"
                "  Run [bold cyan]docto-trace login[/bold cyan] to authenticate.",
                border_style="green",
            )
        )
    except (json.JSONDecodeError, KeyError):
        console.print(
            "[bold red]❌ The file does not look like a valid credentials JSON.[/bold red]\n"
            "  Make sure you downloaded the [bold]OAuth client ID[/bold] JSON, not a service account key."
        )
        raise typer.Exit(code=1)
