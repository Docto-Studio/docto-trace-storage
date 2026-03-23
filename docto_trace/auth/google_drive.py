"""Google Drive authentication — OAuth2 user flow + service account support."""

from __future__ import annotations

from pathlib import Path

import httplib2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import Resource, build
from rich.console import Console

from docto_trace.auth.token_store import load_token, save_token

# Socket timeout for all Drive API HTTP calls (seconds).
# The default httplib2 timeout is ~20 s, which is too short for large pagination
# responses or slow network conditions.
SOCKET_TIMEOUT = 120


def _build_http(creds: Credentials) -> AuthorizedHttp:
    """Return an ``AuthorizedHttp`` transport with an explicit socket timeout."""
    return AuthorizedHttp(creds, http=httplib2.Http(timeout=SOCKET_TIMEOUT))

console = Console(stderr=True)

# Read-only Drive scopes — enforces the "Read-Only by Default" design principle.
READONLY_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def build_drive_service(
    credentials_path: Path,
    token_path: Path,
    service_account_path: Path | None = None,
    scopes: list[str] | None = None,
) -> Resource:
    """
    Build and return an authenticated Google Drive v3 service resource.

    Authentication precedence:
      1. Service account JSON (if ``service_account_path`` is provided).
      2. Cached OAuth2 token (``token.json``).
      3. Interactive OAuth2 browser flow (creates + caches a new token).

    Args:
        credentials_path: Path to the OAuth2 Desktop App credentials JSON.
        token_path: Path where the user token is cached after first login.
        service_account_path: Optional path to a service account key JSON.
        scopes: OAuth2 scopes to request. Defaults to read-only Drive scopes.

    Returns:
        An authenticated ``googleapiclient.discovery.Resource`` for Drive v3.

    Raises:
        FileNotFoundError: If ``credentials_path`` is missing and no cached
            token or service account is available.
        google.auth.exceptions.TransportError: On network failures during auth.
    """
    if scopes is None:
        scopes = READONLY_SCOPES

    creds: Credentials | None = None

    # --- Path 1: Service Account ---
    if service_account_path and service_account_path.exists():
        console.print(
            f"[cyan]🔑 Using service account:[/cyan] {service_account_path}"
        )
        sa_creds = service_account.Credentials.from_service_account_file(
            str(service_account_path), scopes=scopes
        )
        http = AuthorizedHttp(sa_creds, http=httplib2.Http(timeout=SOCKET_TIMEOUT))
        return build("drive", "v3", http=http, cache_discovery=False)

    # --- Path 2: Cached Token ---
    creds = load_token(token_path, scopes)

    if creds and creds.expired and creds.refresh_token:
        try:
            console.print("[cyan]🔄 Refreshing cached token…[/cyan]")
            creds.refresh(Request())
            save_token(creds, token_path)
        except RefreshError:
            console.print(
                "[yellow]⚠️  Token refresh failed — starting new OAuth2 flow.[/yellow]"
            )
            creds = None

    # --- Path 3: Interactive OAuth2 Flow ---
    if not creds or not creds.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"credentials.json not found at '{credentials_path}'.\n"
                "Download it from Google Cloud Console → APIs & Services → Credentials."
            )

        console.print(
            "[cyan]🌐 Opening browser for Google Drive authorization…[/cyan]"
        )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), scopes=scopes
        )
        # run_local_server opens the browser and starts a local redirect server.
        creds = flow.run_local_server(port=0, open_browser=True)
        save_token(creds, token_path)
        console.print(f"[green]✅ Token saved to {token_path}[/green]")

    return build("drive", "v3", http=_build_http(creds), cache_discovery=False)
