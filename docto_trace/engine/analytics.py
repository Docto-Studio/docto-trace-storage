"""
Analytics engine — produces structural insights from a resolved StorageTree.

Phase 1: top-largest folders, deep folders.
Phase 2 stubs: zombie file detection, deduplication.
"""

from __future__ import annotations

from docto_trace.schemas.report import FolderInsight, InsightSummary
from docto_trace.schemas.storage import FolderNode, StorageTree


def _human_readable_size(size_bytes: int) -> str:
    """Convert byte count to a human-readable string (e.g. '3.2 GB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} PB"


def _flatten_folders(
    node: FolderNode,
    path: str = "",
    result: list[FolderInsight] | None = None,
) -> list[FolderInsight]:
    """
    Depth-first traversal that collects every FolderNode as a FolderInsight.

    Args:
        node: The current folder node.
        path: Breadcrumb path built up from the root.
        result: Accumulator list (creates a new list if None).

    Returns:
        A flat list of FolderInsight objects for every folder in the tree.
    """
    if result is None:
        result = []

    breadcrumb = f"{path}/{node.name}" if path else node.name

    result.append(
        FolderInsight(
            folder_id=node.id,
            name=node.name,
            path=breadcrumb,
            depth=node.depth,
            total_size_bytes=node.total_size_bytes,
            total_size_human=_human_readable_size(node.total_size_bytes),
            file_count=node.total_file_count,
        )
    )

    for child in node.children:
        if isinstance(child, FolderNode):
            _flatten_folders(child, path=breadcrumb, result=result)

    return result


def top_folders(tree: StorageTree, n: int = 10) -> list[FolderInsight]:
    """
    Return the top-N folders by cumulative descendant file size.

    Args:
        tree: The fully resolved StorageTree.
        n: Number of folders to return.

    Returns:
        Sorted list of FolderInsight, largest first.
    """
    all_folders = _flatten_folders(tree.tree)
    # Exclude the scan root (depth 0): it always totals everything and adds no insight.
    non_root = [f for f in all_folders if f.depth > 0]
    return sorted(non_root, key=lambda f: f.total_size_bytes, reverse=True)[:n]


def deep_folders(tree: StorageTree, threshold: int = 5) -> list[FolderInsight]:
    """
    Return all folders whose depth meets or exceeds ``threshold``.

    Args:
        tree: The fully resolved StorageTree.
        threshold: Minimum depth to flag a folder as 'deep'.

    Returns:
        List of FolderInsight sorted by depth (deepest first).
    """
    all_folders = _flatten_folders(tree.tree)
    flagged = [f for f in all_folders if f.depth >= threshold]
    return sorted(flagged, key=lambda f: f.depth, reverse=True)


def build_insight_summary(
    tree: StorageTree,
    top_n: int = 10,
    deep_folder_threshold: int = 5,
) -> InsightSummary:
    """
    Run all Phase 1 analytics and return a single InsightSummary.

    Args:
        tree: The fully resolved StorageTree.
        top_n: How many top folders to include.
        deep_folder_threshold: Nesting depth to flag as 'deep'.

    Returns:
        An InsightSummary ready for embedding in a HealthReport.
    """
    return InsightSummary(
        top_folders=top_folders(tree, n=top_n),
        deep_folders=deep_folders(tree, threshold=deep_folder_threshold),
        top_n=top_n,
        deep_folder_threshold=deep_folder_threshold,
    )
