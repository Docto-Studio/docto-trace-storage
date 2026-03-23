"""
Phase 2 Audit Engine — Zombie detection and content deduplication.

Design principles
-----------------
* **Pure functions** — same pattern as ``analytics.py``.  No I/O, no side
  effects, trivially unit-testable with in-memory fixtures.
* **Single pass** — both ``find_zombies`` and ``find_duplicates`` flatten the
  tree once internally; callers that need both should use
  ``build_audit_summary()`` to avoid redundant traversals.
* **Graceful degradation** — missing ``md5_checksum`` values fall back to a
  ``(size_bytes, normalized_name)`` surrogate key so Google-native formats
  (Docs, Sheets) are still caught when renamed.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Generator

from dateutil.relativedelta import relativedelta

from docto_trace.schemas.report import (
    ActionItem,
    ActionSeverity,
    DuplicateGroup,
    ZombieFile,
    ZombieStatus,
)
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_WASTED_BYTES_CRITICAL_THRESHOLD = 100 * 1024 * 1024  # 100 MB


def _iter_files(node: FolderNode) -> Generator[tuple[FileNode, str], None, None]:
    """
    Depth-first generator that yields ``(FileNode, breadcrumb_path)`` for
    every non-folder descendant of *node*.

    Args:
        node: Root folder to start traversal from.

    Yields:
        Tuples of ``(FileNode, path_string)``.
    """
    stack: list[tuple[FolderNode, str]] = [(node, node.name)]
    while stack:
        current, path = stack.pop()
        for child in current.children:
            if isinstance(child, FolderNode):
                stack.append((child, f"{path}/{child.name}"))
            else:
                yield child, f"{path}/{child.name}"


# ---------------------------------------------------------------------------
# FR4 — Zombie File Detection
# ---------------------------------------------------------------------------


def find_zombies(
    tree: StorageTree,
    threshold_months: int = 24,
) -> list[ZombieFile]:
    """
    Return every file that has not been modified within *threshold_months*.

    A file with ``modified_at = None`` is considered stale: the Drive API
    did not report a modification time, which is treated conservatively as
    "unknown age" and therefore potentially stale.

    Files are returned sorted from stalest to most-recently-modified
    (files with ``None`` dates come last, as their age is indeterminate).

    Args:
        tree: The fully resolved ``StorageTree`` from a scan.
        threshold_months: Number of months with no modification before a file
            is flagged. Defaults to 24 (2 years).

    Returns:
        A list of ``ZombieFile`` instances, stalest first.
    """
    cutoff = datetime.now(UTC) - relativedelta(months=threshold_months)
    zombies: list[ZombieFile] = []
    none_date: list[ZombieFile] = []  # Collect unknowns separately for ordering.

    for file_node, path in _iter_files(tree.tree):
        if file_node.modified_at is None:
            none_date.append(
                ZombieFile(
                    file_id=file_node.id,
                    name=file_node.name,
                    path=path,
                    last_modified=None,
                    size_bytes=file_node.size_bytes,
                    web_view_link=file_node.web_view_link,
                    reason=ZombieStatus.STALE,
                )
            )
        elif file_node.modified_at < cutoff:
            zombies.append(
                ZombieFile(
                    file_id=file_node.id,
                    name=file_node.name,
                    path=path,
                    last_modified=file_node.modified_at,
                    size_bytes=file_node.size_bytes,
                    web_view_link=file_node.web_view_link,
                    reason=ZombieStatus.STALE,
                )
            )

    # Sort known-date zombies stalest-first, then append unknowns.
    zombies.sort(key=lambda z: z.last_modified or datetime.min.replace(tzinfo=UTC))
    return zombies + none_date


# ---------------------------------------------------------------------------
# FR5 — Content Fingerprinting / Deduplication
# ---------------------------------------------------------------------------


def find_duplicates(tree: StorageTree) -> list[DuplicateGroup]:
    """
    Group files that share identical content into ``DuplicateGroup`` instances.

    Fingerprinting strategy (two-tier):
    1. **Primary key** — ``md5_checksum`` from the Drive API, when available.
       This covers binary files (PDFs, images, Office docs, etc.).
    2. **Fallback key** — ``"<size_bytes>:<normalized_name>"`` where
       ``normalized_name = name.lower().strip()``.  This catches Google-native
       files (Docs, Sheets, Slides) for which Drive does not compute an MD5,
       and renamed copies that happen to be the same size.

    Groups with only one member are discarded (not duplicates).
    The result is sorted by ``wasted_bytes`` descending (most wasteful first).

    Args:
        tree: The fully resolved ``StorageTree`` from a scan.

    Returns:
        A list of ``DuplicateGroup`` instances, most-wasteful first.
    """
    # bucket: fingerprint → list of (FileNode, path)
    buckets: defaultdict[str, list[tuple[FileNode, str]]] = defaultdict(list)

    for file_node, path in _iter_files(tree.tree):
        if file_node.md5_checksum:
            key = file_node.md5_checksum
        else:
            normalized = file_node.name.lower().strip()
            key = f"{file_node.size_bytes}:{normalized}"
        buckets[key].append((file_node, path))

    groups: list[DuplicateGroup] = []
    for fingerprint, entries in buckets.items():
        if len(entries) < 2:
            continue  # Unique — not a duplicate.

        # Use the size of the first node as the canonical copy size.
        # For md5-keyed groups all nodes have identical content, so any size
        # is representative.  For fallback-keyed groups sizes are equal by
        # construction.
        size_per_copy = entries[0][0].size_bytes
        wasted = size_per_copy * (len(entries) - 1)

        groups.append(
            DuplicateGroup(
                fingerprint=fingerprint,
                files=[n.id for n, _ in entries],
                file_names=[n.name for n, _ in entries],
                file_paths=[p for _, p in entries],
                size_bytes_per_copy=size_per_copy,
                wasted_bytes=wasted,
            )
        )

    return sorted(groups, key=lambda g: g.wasted_bytes, reverse=True)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_audit_summary(
    tree: StorageTree,
    stale_threshold_months: int = 24,
) -> tuple[list[ZombieFile], list[DuplicateGroup], list[ActionItem]]:
    """
    Run all Phase 2 audits and return a single cohesive result.

    Calls ``find_zombies`` and ``find_duplicates``, and generates a list of
    ``ActionItem`` objects for the remediation plan embedded in the report.

    Args:
        tree: The fully resolved ``StorageTree``.
        stale_threshold_months: Staleness cutoff; forwarded to ``find_zombies``.

    Returns:
        A 3-tuple of ``(zombies, duplicate_groups, action_items)``.
    """
    zombies = find_zombies(tree, threshold_months=stale_threshold_months)
    duplicates = find_duplicates(tree)
    action_items = _build_action_items(zombies, duplicates)
    return zombies, duplicates, action_items


def _build_action_items(
    zombies: list[ZombieFile],
    duplicates: list[DuplicateGroup],
) -> list[ActionItem]:
    """Derive ``ActionItem`` entries from audit findings."""
    items: list[ActionItem] = []

    if zombies:
        total_zombie_bytes = sum(z.size_bytes for z in zombies)
        items.append(
            ActionItem(
                severity=ActionSeverity.WARNING,
                category="zombie",
                description=(
                    f"{len(zombies)} stale file(s) found that have not been modified "
                    f"in over {total_zombie_bytes // (1024**2)} MB of storage. "
                    "Review and delete or archive to free space."
                ),
                affected_ids=[z.file_id for z in zombies],
            )
        )

    total_wasted = sum(d.wasted_bytes for d in duplicates)
    if duplicates:
        severity = (
            ActionSeverity.CRITICAL
            if total_wasted >= _WASTED_BYTES_CRITICAL_THRESHOLD
            else ActionSeverity.WARNING
        )
        items.append(
            ActionItem(
                severity=severity,
                category="duplicate",
                description=(
                    f"{len(duplicates)} duplicate group(s) detected, "
                    f"wasting ~{total_wasted // (1024**2)} MB. "
                    "Delete redundant copies to reclaim storage."
                ),
                affected_ids=[fid for d in duplicates for fid in d.files],
            )
        )

    return items
