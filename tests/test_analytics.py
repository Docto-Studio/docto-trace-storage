"""Unit tests for the analytics engine."""

from __future__ import annotations

from docto_trace.engine.analytics import (
    _human_readable_size,
    build_insight_summary,
    deep_folders,
    top_folders,
)
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(name: str, size: int, depth: int = 1) -> FileNode:
    return FileNode(id=name, name=name, mime_type="application/pdf", size_bytes=size, depth=depth)


def _build_tree() -> StorageTree:
    """
    Build this synthetic tree:

        root/ (depth 0)
          ├── BigDocs/ (depth 1)  — 50 MB
          │     ├── really_big.pdf  50 MB
          │     └── Nested1/ (depth 2)
          │           └── Nested2/ (depth 3)
          │                 └── Nested3/ (depth 4)
          │                       └── Nested4/ (depth 5) ← deep!
          │                             └── deep_file.txt  1 KB
          └── SmallDocs/ (depth 1) — 100 KB
                ├── a.txt  60 KB
                └── b.txt  40 KB
    """
    MB = 1024 * 1024
    KB = 1024

    # Build bottom-up so stats accumulate correctly.
    nested4 = FolderNode(id="nested4", name="Nested4", depth=5)
    nested4.add_child(_make_file("deep_file.txt", 1 * KB, depth=6))

    nested3 = FolderNode(id="nested3", name="Nested3", depth=4)
    nested3.add_child(nested4)

    nested2 = FolderNode(id="nested2", name="Nested2", depth=3)
    nested2.add_child(nested3)

    nested1 = FolderNode(id="nested1", name="Nested1", depth=2)
    nested1.add_child(nested2)

    big_docs = FolderNode(id="bigdocs", name="BigDocs", depth=1)
    big_docs.add_child(_make_file("really_big.pdf", 50 * MB, depth=2))
    big_docs.add_child(nested1)

    small_docs = FolderNode(id="smalldocs", name="SmallDocs", depth=1)
    small_docs.add_child(_make_file("a.txt", 60 * KB, depth=2))
    small_docs.add_child(_make_file("b.txt", 40 * KB, depth=2))

    root = FolderNode(id="root", name="My Drive", depth=0)
    root.add_child(big_docs)
    root.add_child(small_docs)

    return StorageTree(root_id="root", root_name="My Drive", tree=root)


# ---------------------------------------------------------------------------
# _human_readable_size
# ---------------------------------------------------------------------------


class TestHumanReadableSize:
    def test_bytes(self):
        assert _human_readable_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert _human_readable_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert _human_readable_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert _human_readable_size(3 * 1024 ** 3) == "3.0 GB"


# ---------------------------------------------------------------------------
# top_folders
# ---------------------------------------------------------------------------


class TestTopFolders:
    def test_returns_correct_count(self):
        tree = _build_tree()
        result = top_folders(tree, n=3)
        assert len(result) <= 3

    def test_sorted_largest_first(self):
        tree = _build_tree()
        result = top_folders(tree, n=10)
        sizes = [f.total_size_bytes for f in result]
        assert sizes == sorted(sizes, reverse=True)

    def test_largest_is_bigdocs(self):
        tree = _build_tree()
        result = top_folders(tree, n=10)
        # BigDocs should be the largest non-root folder.
        non_root = [f for f in result if f.folder_id != "root"]
        assert non_root[0].folder_id == "bigdocs"

    def test_n_equals_zero_returns_empty(self):
        tree = _build_tree()
        assert top_folders(tree, n=0) == []

    def test_excludes_root(self):
        tree = _build_tree()
        result = top_folders(tree, n=10)
        ids = [f.folder_id for f in result]
        assert "root" not in ids


# ---------------------------------------------------------------------------
# deep_folders
# ---------------------------------------------------------------------------


class TestDeepFolders:
    def test_finds_nested4_at_threshold_5(self):
        tree = _build_tree()
        result = deep_folders(tree, threshold=5)
        ids = [f.folder_id for f in result]
        assert "nested4" in ids

    def test_does_not_flag_shallow_folders(self):
        tree = _build_tree()
        result = deep_folders(tree, threshold=5)
        ids = [f.folder_id for f in result]
        # bigdocs is depth 1, should not be flagged.
        assert "bigdocs" not in ids

    def test_sorted_deepest_first(self):
        tree = _build_tree()
        result = deep_folders(tree, threshold=3)
        depths = [f.depth for f in result]
        assert depths == sorted(depths, reverse=True)

    def test_high_threshold_returns_empty(self):
        tree = _build_tree()
        result = deep_folders(tree, threshold=100)
        assert result == []


# ---------------------------------------------------------------------------
# build_insight_summary
# ---------------------------------------------------------------------------


class TestBuildInsightSummary:
    def test_summary_contains_correct_top_n(self):
        tree = _build_tree()
        summary = build_insight_summary(tree, top_n=3, deep_folder_threshold=5)
        assert summary.top_n == 3
        assert len(summary.top_folders) <= 3

    def test_summary_threshold_is_recorded(self):
        tree = _build_tree()
        summary = build_insight_summary(tree, top_n=10, deep_folder_threshold=7)
        assert summary.deep_folder_threshold == 7
