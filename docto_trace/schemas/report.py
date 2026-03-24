"""
Pydantic v2 report data models for docto-trace-storage.

Phase 1 (v0.1): structural insights (top folders, deep folders).
Phase 2 (v0.2): zombie detection, deduplication (stubs included).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from docto_trace.schemas.storage import StorageTree


# ---------------------------------------------------------------------------
# Phase 1 — Structural Insights
# ---------------------------------------------------------------------------


class FolderInsight(BaseModel):
    """A flattened view of a single folder for reporting purposes."""

    folder_id: str
    name: str
    path: str = Field(description="Human-readable breadcrumb path from the scan root.")
    depth: int
    total_size_bytes: int
    total_size_human: str = Field(description="Human-readable size string, e.g. '3.2 GB'.")
    file_count: int


class InsightSummary(BaseModel):
    """Aggregated structural insights produced by the analytics engine."""

    top_folders: list[FolderInsight] = Field(
        default_factory=list,
        description="Top-N largest folders by cumulative file size.",
    )
    deep_folders: list[FolderInsight] = Field(
        default_factory=list,
        description="Folders whose nesting depth exceeds the configured threshold.",
    )
    top_n: int = Field(description="The N used to compute top_folders.")
    deep_folder_threshold: int = Field(
        description="The depth threshold used to compute deep_folders."
    )


# ---------------------------------------------------------------------------
# Phase 2 stubs (v0.2)
# ---------------------------------------------------------------------------


class ZombieStatus(str, Enum):
    STALE = "stale"
    ORPHANED = "orphaned"


class ZombieFile(BaseModel):
    """A file flagged as a potential zombie (Phase 2)."""

    file_id: str
    name: str
    path: str = Field(description="Human-readable breadcrumb path from the scan root.")
    last_modified: datetime | None
    size_bytes: int = Field(default=0, ge=0)
    web_view_link: str | None = Field(default=None)
    reason: ZombieStatus


class DuplicateGroup(BaseModel):
    """A group of files sharing the same content fingerprint (Phase 2)."""

    fingerprint: str = Field(
        description="MD5 checksum (binary files) or '<size>:<normalized_name>' (fallback)."
    )
    files: list[str] = Field(description="File IDs sharing this fingerprint.")
    file_names: list[str] = Field(
        default_factory=list,
        description="Display names corresponding to each file ID (same order).",
    )
    file_paths: list[str] = Field(
        default_factory=list,
        description="Breadcrumb Drive paths corresponding to each file ID (same order).",
    )
    size_bytes_per_copy: int = Field(
        default=0, ge=0, description="Size of a single copy in bytes."
    )
    wasted_bytes: int = Field(
        description="Bytes consumed by the redundant copies (total_size - 1 copy)."
    )


class ActionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActionItem(BaseModel):
    """A single suggested action in the remediation plan."""

    severity: ActionSeverity
    category: str = Field(description="e.g. 'deep_folder', 'zombie', 'duplicate'")
    description: str
    affected_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4 stubs (AI Readiness)
# ---------------------------------------------------------------------------


class FileTypeCategory(str, Enum):
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    UNKNOWN = "unknown"


class AIReadinessScore(BaseModel):
    """Evaluates the readiness of the storage for AI and Search indexing."""

    structured_files_count: int = Field(default=0, ge=0)
    unstructured_files_count: int = Field(default=0, ge=0)
    structured_bytes: int = Field(default=0, ge=0)
    unstructured_bytes: int = Field(default=0, ge=0)
    naming_entropy_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Programmatic score (0-100) evaluating descriptiveness of file names.",
    )
    ai_analysis_report: str | None = Field(
        default=None,
        description="Qualitative generated report by an LLM, if enabled.",
    )


# ---------------------------------------------------------------------------
# Quota summary (from Drive about.get)
# ---------------------------------------------------------------------------


class QuotaSummary(BaseModel):
    """
    Google account storage quota as reported by Drive about.get().

    Covers ALL Google storage: Drive + Gmail + Google Photos.
    This matches the numbers shown in the Google Drive UI.
    """

    total_bytes: int = Field(
        default=0,
        description="Total bytes used across Drive + Gmail + Photos (usage).",
    )
    drive_bytes: int = Field(
        default=0,
        description="Bytes used by Drive files only (usageInDrive).",
    )
    trash_bytes: int = Field(
        default=0,
        description="Bytes used by Drive trash (usageInDriveTrash).",
    )
    other_bytes: int = Field(
        default=0,
        description="Bytes used by Gmail + Photos = total_bytes - drive_bytes.",
    )
    limit_bytes: int = Field(
        default=0,
        description="Total storage limit (0 = unlimited / could not be determined).",
    )


# ---------------------------------------------------------------------------
# Top-level Report
# ---------------------------------------------------------------------------


class HealthReport(BaseModel):
    """
    The canonical Docto Trace health report.

    Schema-first: every field is typed so downstream Docto modules
    (Form, Flux, Echo) can consume this without guessing.
    """

    schema_version: str = Field(default="0.2.0")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(default="google", description="Scan source: 'google' or 'local'.")

    # Core scan result
    storage_tree: StorageTree

    # Google account quota (from about.get — includes Gmail + Photos)
    quota: QuotaSummary | None = Field(
        default=None,
        description="Full Google account storage quota. None if the call failed.",
    )

    # Phase 1 insights
    insights: InsightSummary

    # Phase 2 fields (empty in v0.1)
    zombies: list[ZombieFile] = Field(default_factory=list)
    duplicates: list[DuplicateGroup] = Field(default_factory=list)
    action_plan: list[ActionItem] = Field(default_factory=list)

    # Phase 4 fields
    ai_readiness: AIReadinessScore | None = Field(default=None)
