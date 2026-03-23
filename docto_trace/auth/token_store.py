"""Token serialization helpers for Google OAuth2 credentials."""

import json
from pathlib import Path

from google.oauth2.credentials import Credentials


def save_token(credentials: Credentials, token_path: Path) -> None:
    """Persist a Credentials object to disk as JSON."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or []),
    }
    token_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_token(token_path: Path, scopes: list[str]) -> Credentials | None:
    """
    Load a cached Credentials object from disk.

    Returns None if the file doesn't exist or contains unexpected data.
    """
    if not token_path.exists():
        return None
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        creds = Credentials(
            token=data["token"],
            refresh_token=data["refresh_token"],
            token_uri=data["token_uri"],
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scopes=data.get("scopes", scopes),
        )
        return creds
    except (KeyError, json.JSONDecodeError):
        return None
