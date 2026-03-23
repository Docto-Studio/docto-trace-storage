"""
Pydantic v2 storage data models for docto-trace-storage.

These represent the raw data discovered during a Drive scan.
Every model is schema-first and JSON-serializable to ensure
compatibility with future Docto modules (Form, Flux, Echo).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Union

from pydantic import BaseModel, Field, model_validator


class FileNode(BaseModel):
    """A single non-folder file discovered in Google Drive."""

    id: str = Field(description="Google Drive file ID.")
    name: str = Field(description="Display name of the file.")
    mime_type: str = Field(description="MIME type as reported by Drive.")
    size_bytes: int = Field(default=0, ge=0, description="File size in bytes.")
    created_at: datetime | None = Field(default=None)
    modified_at: datetime | None = Field(default=None)
    owners: list[str] = Field(
        default_factory=list,
        description="Email addresses of the file's owners.",
    )
    parents: list[str] = Field(
        default_factory=list,
        description="Parent folder IDs (Drive supports multiple parents).",
    )
    web_view_link: str | None = Field(
        default=None, description="Shareable browser link."
    )
    depth: int = Field(default=0, ge=0, description="Nesting depth from the scan root.")
    md5_checksum: str | None = Field(
        default=None,
        description=(
            "MD5 checksum as reported by the Drive API (md5Checksum). "
            "Available for binary files only; None for Google-native formats."
        ),
    )


class FolderNode(BaseModel):
    """
    A folder discovered in Google Drive, with its children recursively resolved.
    """

    id: str = Field(description="Google Drive folder ID.")
    name: str = Field(description="Display name of the folder.")
    children: list[Annotated[Union[FileNode, FolderNode], Field(discriminator=None)]] = Field(
        default_factory=list,
        description="Direct children (files and sub-folders).",
    )
    total_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Cumulative size of all descendant files (bytes).",
    )
    total_file_count: int = Field(
        default=0,
        ge=0,
        description="Total number of descendant files (non-folders).",
    )
    depth: int = Field(default=0, ge=0, description="Nesting depth from the scan root.")
    parents: list[str] = Field(default_factory=list)
    web_view_link: str | None = Field(default=None)

    def add_child(self, child: FileNode | FolderNode) -> None:
        """Append a child and accumulate size/count stats."""
        self.children.append(child)
        if isinstance(child, FileNode):
            self.total_size_bytes += child.size_bytes
            self.total_file_count += 1
        else:
            self.total_size_bytes += child.total_size_bytes
            self.total_file_count += child.total_file_count


class StorageTree(BaseModel):
    """The complete storage snapshot returned by a scan."""

    root_id: str = Field(description="Drive ID of the scan root (e.g. 'root').")
    root_name: str = Field(description="Display name of the scan root.")
    tree: FolderNode = Field(description="Fully resolved recursive folder tree.")
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_files: int = Field(default=0, ge=0)
    total_folders: int = Field(default=0, ge=0)
    total_size_bytes: int = Field(default=0, ge=0)
    max_depth_reached: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _sync_stats_from_tree(self) -> StorageTree:
        """Populate top-level stats from the resolved tree if they are still zero."""
        if self.total_files == 0 and self.total_size_bytes == 0:
            self.total_files = self.tree.total_file_count
            self.total_size_bytes = self.tree.total_size_bytes
        return self
