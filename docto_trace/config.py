"""Runtime configuration for docto-trace-storage."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Docto Trace runtime settings.

    All values can be overridden via environment variables prefixed with DOCTO_TRACE_.
    Example: DOCTO_TRACE_MAX_DEPTH=10 docto-trace scan
    """

    model_config = SettingsConfigDict(
        env_prefix="DOCTO_TRACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Auth ---
    credentials_path: Path = Field(
        default=Path("credentials.json"),
        description="Path to your Google OAuth2 Desktop App credentials JSON file.",
    )
    token_path: Path = Field(
        default=Path("token.json"),
        description="Where to cache the user's OAuth2 token after first login.",
    )
    service_account_path: Path | None = Field(
        default=None,
        description="Path to a service account JSON key (overrides OAuth2 user flow).",
    )

    # --- Traversal ---
    max_depth: int | None = Field(
        default=None,
        description="Maximum folder depth to traverse. None = unlimited.",
    )
    deep_folder_threshold: int = Field(
        default=5,
        description="Minimum nesting depth to flag a folder as 'deep'.",
    )
    top_n: int = Field(
        default=10,
        description="Number of top-largest folders to surface in the report.",
    )

    # --- Audit (Phase 2) ---
    stale_threshold_months: int = Field(
        default=24,
        ge=1,
        description=(
            "Files not modified within this many months are flagged as zombies. "
            "Override with DOCTO_TRACE_STALE_THRESHOLD_MONTHS."
        ),
    )

    # --- Output ---
    output_dir: Path = Field(
        default=Path("output"),
        description="Directory where report.json and other outputs are written.",
    )

    # --- API ---
    page_size: int = Field(
        default=1000,
        ge=1,
        le=1000,
        description="Files per page when listing Drive items (max 1000).",
    )
    max_retries: int = Field(
        default=5,
        description="Maximum exponential back-off retries on 429/503 errors.",
    )


# Singleton — import this everywhere instead of creating new instances.
settings = Settings()
