"""Unit tests for the Phase 2 audit engine (auditor.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from docto_trace.engine.auditor import find_duplicates, find_zombies
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

MB = 1024 * 1024


def _make_file(
    name: str,
    size: int = 1 * MB,
    depth: int = 1,
    modified_at: datetime | None = None,
    md5: str | None = None,
    file_id: str | None = None,
) -> FileNode:
    return FileNode(
        id=file_id or name,
        name=name,
        mime_type="application/pdf",
        size_bytes=size,
        depth=depth,
        modified_at=modified_at,
        md5_checksum=md5,
    )


def _build_tree(*files: FileNode) -> StorageTree:
    """Wrap a flat list of files in a minimal StorageTree."""
    root = FolderNode(id="root", name="My Drive", depth=0)
    for f in files:
        root.add_child(f)
    return StorageTree(root_id="root", root_name="My Drive", tree=root)


def _now() -> datetime:
    return datetime.now(UTC)


def _ago(months: int) -> datetime:
    """Return a timezone-aware datetime *months* months in the past."""
    # Use timedelta(days=30*months) for consistent, test-friendly arithmetic.
    return _now() - timedelta(days=30 * months)


# ---------------------------------------------------------------------------
# FR4 — find_zombies
# ---------------------------------------------------------------------------


class TestFindZombies:
    def test_stale_file_is_flagged(self):
        """A file modified 36 months ago must appear in the zombie list."""
        stale = _make_file("old.pdf", modified_at=_ago(36))
        tree = _build_tree(stale)
        result = find_zombies(tree, threshold_months=24)
        assert any(z.file_id == "old.pdf" for z in result)

    def test_recent_file_not_flagged(self):
        """A file modified 1 month ago must not be flagged."""
        recent = _make_file("new.pdf", modified_at=_ago(1))
        tree = _build_tree(recent)
        result = find_zombies(tree, threshold_months=24)
        assert not any(z.file_id == "new.pdf" for z in result)

    def test_file_at_threshold_boundary_not_flagged(self):
        """A file modified exactly at the boundary (now - threshold) must NOT be flagged."""
        # Use 23-month-old file with 24-month threshold → should be safe.
        borderline = _make_file("border.pdf", modified_at=_ago(23))
        tree = _build_tree(borderline)
        result = find_zombies(tree, threshold_months=24)
        assert not any(z.file_id == "border.pdf" for z in result)

    def test_none_modified_date_flagged(self):
        """Files with unknown modified dates (None) must be flagged as stale."""
        unknown = _make_file("unknown.pdf", modified_at=None)
        tree = _build_tree(unknown)
        result = find_zombies(tree, threshold_months=24)
        assert any(z.file_id == "unknown.pdf" for z in result)

    def test_none_date_zombies_sorted_last(self):
        """Files with known stale dates should appear before None-date files."""
        stale = _make_file("stale.pdf", modified_at=_ago(36), file_id="stale")
        unknown = _make_file("unknown.pdf", modified_at=None, file_id="unknown")
        tree = _build_tree(stale, unknown)
        result = find_zombies(tree, threshold_months=24)
        ids = [z.file_id for z in result]
        assert ids.index("stale") < ids.index("unknown")

    def test_sorted_stalest_first(self):
        """Zombies must be sorted from oldest to most-recently-modified."""
        a = _make_file("a.pdf", modified_at=_ago(60), file_id="a")
        b = _make_file("b.pdf", modified_at=_ago(30), file_id="b")
        tree = _build_tree(a, b)
        result = find_zombies(tree, threshold_months=24)
        ids = [z.file_id for z in result]
        assert ids.index("a") < ids.index("b")

    def test_zombie_file_has_path(self):
        """Each ZombieFile must carry a non-empty breadcrumb path."""
        stale = _make_file("doc.pdf", modified_at=_ago(36))
        tree = _build_tree(stale)
        result = find_zombies(tree, threshold_months=24)
        assert result[0].path  # Non-empty string.

    def test_empty_tree_returns_empty(self):
        """An empty tree must return an empty zombie list."""
        root = FolderNode(id="root", name="My Drive", depth=0)
        tree = StorageTree(root_id="root", root_name="My Drive", tree=root)
        result = find_zombies(tree, threshold_months=24)
        assert result == []

    def test_custom_threshold_respected(self):
        """A 6-month threshold should flag a 7-month-old file."""
        stale = _make_file("old.pdf", modified_at=_ago(7), file_id="seven")
        recent = _make_file("new.pdf", modified_at=_ago(5), file_id="five")
        tree = _build_tree(stale, recent)
        result = find_zombies(tree, threshold_months=6)
        ids = [z.file_id for z in result]
        assert "seven" in ids
        assert "five" not in ids


# ---------------------------------------------------------------------------
# FR5 — find_duplicates
# ---------------------------------------------------------------------------


class TestFindDuplicates:
    def test_md5_duplicates_grouped(self):
        """Two files with the same md5 checksum must form one duplicate group."""
        a = _make_file("invoice_final.pdf", md5="abc123", file_id="f1")
        b = _make_file("copy_of_invoice.pdf", md5="abc123", file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert len(result) == 1
        assert set(result[0].files) == {"f1", "f2"}

    def test_unique_files_no_groups(self):
        """Files with unique md5 checksums must produce no duplicate groups."""
        a = _make_file("a.pdf", md5="aaa111", file_id="f1")
        b = _make_file("b.pdf", md5="bbb222", file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert result == []

    def test_wasted_bytes_calculation(self):
        """wasted_bytes must equal size_bytes * (count - 1)."""
        size = 5 * MB
        a = _make_file("file.pdf", size=size, md5="deadbeef", file_id="f1")
        b = _make_file("file_copy.pdf", size=size, md5="deadbeef", file_id="f2")
        c = _make_file("file_bak.pdf", size=size, md5="deadbeef", file_id="f3")
        tree = _build_tree(a, b, c)
        result = find_duplicates(tree)
        assert len(result) == 1
        assert result[0].wasted_bytes == size * 2  # 3 copies - 1 = 2 wasted.

    def test_sorted_most_wasteful_first(self):
        """Groups should be ordered by wasted_bytes descending."""
        # Group A: 2 copies × 10 MB → 10 MB wasted
        a1 = _make_file("big1.pdf", size=10 * MB, md5="aaa", file_id="a1")
        a2 = _make_file("big2.pdf", size=10 * MB, md5="aaa", file_id="a2")
        # Group B: 2 copies × 1 MB → 1 MB wasted
        b1 = _make_file("small1.pdf", size=1 * MB, md5="bbb", file_id="b1")
        b2 = _make_file("small2.pdf", size=1 * MB, md5="bbb", file_id="b2")
        tree = _build_tree(a1, a2, b1, b2)
        result = find_duplicates(tree)
        assert result[0].wasted_bytes >= result[1].wasted_bytes

    def test_fallback_name_size_grouping(self):
        """Files without md5 but with same (size, normalized_name) must be grouped."""
        name = "Budget Report"
        size = 2 * MB
        a = _make_file(name, size=size, md5=None, file_id="f1")
        b = _make_file(name, size=size, md5=None, file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert len(result) == 1
        assert set(result[0].files) == {"f1", "f2"}

    def test_fallback_different_size_not_grouped(self):
        """Same name but different sizes must NOT be grouped under the fallback."""
        a = _make_file("report.pdf", size=1 * MB, md5=None, file_id="f1")
        b = _make_file("report.pdf", size=2 * MB, md5=None, file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert result == []

    def test_md5_takes_priority_over_name_fallback(self):
        """Files with md5 must be keyed by md5, not by name/size."""
        # Same name and size, but different md5 → not duplicates.
        a = _make_file("doc.pdf", size=1 * MB, md5="aaa", file_id="f1")
        b = _make_file("doc.pdf", size=1 * MB, md5="bbb", file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert result == []

    def test_file_names_included_in_group(self):
        """DuplicateGroup.file_names and file_paths must list each copy's details."""
        a = _make_file("invoice_final.pdf", md5="xyz", file_id="f1")
        b = _make_file("invoice_copy.pdf", md5="xyz", file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert set(result[0].file_names) == {"invoice_final.pdf", "invoice_copy.pdf"}
        # Each file should have a non-empty breadcrumb path.
        assert all(p for p in result[0].file_paths)
        assert len(result[0].file_paths) == 2

    def test_size_bytes_per_copy_is_set(self):
        """DuplicateGroup.size_bytes_per_copy must equal the individual file size."""
        size = 3 * MB
        a = _make_file("a.pdf", size=size, md5="dup", file_id="f1")
        b = _make_file("b.pdf", size=size, md5="dup", file_id="f2")
        tree = _build_tree(a, b)
        result = find_duplicates(tree)
        assert result[0].size_bytes_per_copy == size

    def test_empty_tree_returns_empty(self):
        """An empty tree must return an empty duplicate list."""
        root = FolderNode(id="root", name="My Drive", depth=0)
        tree = StorageTree(root_id="root", root_name="My Drive", tree=root)
        result = find_duplicates(tree)
        assert result == []

    def test_nested_folder_files_found(self):
        """Duplicates inside nested sub-folders must still be detected."""
        sub = FolderNode(id="sub", name="SubFolder", depth=1)
        a = _make_file("nested.pdf", md5="nest", file_id="fa")
        b = _make_file("nested_copy.pdf", md5="nest", file_id="fb")
        sub.add_child(a)

        root = FolderNode(id="root", name="My Drive", depth=0)
        root.add_child(sub)
        root.add_child(b)

        tree = StorageTree(root_id="root", root_name="My Drive", tree=root)
        result = find_duplicates(tree)
        assert len(result) == 1
        assert set(result[0].files) == {"fa", "fb"}
