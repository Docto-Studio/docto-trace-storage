"""
Async iterative folder traversal engine.

Converts a flat stream of Drive API items into a fully resolved
FolderNode tree, tracking depth and accumulating size statistics.

Design notes
------------
The original recursive approach used ``asyncio.gather`` with unbounded
concurrency, which caused a Python stack overflow / segmentation fault on
large Google Drives (hundreds of folders → hundreds of simultaneous threads
through ``run_in_executor`` + deep Python call stacks).

This rewrite uses an **iterative BFS queue** protected by an
``asyncio.Semaphore`` to cap parallel API calls at ``MAX_CONCURRENT``
(default 20).  The tree is built bottom-up: each folder task stores its
result into a shared dict indexed by folder ID; once all tasks are done the
parent–child relationships are wired up in a single post-processing pass.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import NamedTuple, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from docto_trace.connectors.base import AbstractConnector
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree

console = Console(stderr=True)

# Maximum number of concurrent Drive API calls.
MAX_CONCURRENT = 20


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO 8601 string to datetime, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _item_to_file_node(item: dict, depth: int) -> FileNode:
    """Convert a raw provider item dict to a FileNode."""
    owners = [
        o.get("emailAddress", "") for o in item.get("owners", []) if o.get("emailAddress")
    ]
    return FileNode(
        id=item["id"],
        name=item.get("name", "Untitled"),
        mime_type=item.get("mimeType", "application/octet-stream"),
        size_bytes=int(item.get("size", 0)),
        quota_bytes_used=int(item.get("quotaBytesUsed", 0)),
        created_at=_parse_dt(item.get("createdTime")),
        modified_at=_parse_dt(item.get("modifiedTime")),
        owners=owners,
        parents=item.get("parents", []),
        web_view_link=item.get("webViewLink"),
        depth=depth,
        md5_checksum=item.get("md5Checksum"),
    )


class _FolderWork(NamedTuple):
    """Lightweight descriptor for a single folder to be fetched."""
    folder_id: str
    folder_name: str
    depth: int
    parent_id: str | None  # None → this is the scan root


async def _fetch_folder(
    connector: AbstractConnector,
    work: _FolderWork,
    sem: asyncio.Semaphore,
    progress: Progress | None,
    task_id: int | None,
    max_depth: int | None,
    queue: asyncio.Queue[_FolderWork],
    nodes: dict[str, FolderNode],
    children_map: dict[str, list[str | FileNode]],
    _tracker: Any = None,
) -> None:
    """
    Fetch one folder's children under the semaphore guard, then enqueue
    any sub-folders found within the depth limit.
    """
    async with sem:
        items = await connector.list_items(work.folder_id)

    # Create the FolderNode for this folder.
    node = FolderNode(id=work.folder_id, name=work.folder_name, depth=work.depth)
    nodes[work.folder_id] = node

    if progress and task_id is not None:
        progress.advance(task_id, 1)

    folder_mime = connector.get_folder_mime()
    
    local_folders = 0
    local_files = 0

    for item in items:
        if item.get("mimeType") == folder_mime:
            local_folders += 1
            child_depth = work.depth + 1
            # Only enqueue sub-folders within the depth limit.
            if max_depth is None or child_depth < max_depth:
                await queue.put(
                    _FolderWork(
                        folder_id=item["id"],
                        folder_name=item.get("name", "Untitled"),
                        depth=child_depth,
                        parent_id=work.folder_id,
                    )
                )
            # Always record the folder in the children map even if not traversed.
            children_map[work.folder_id].append(item["id"])
            # Pre-create a stub node for depth-limited folders if needed.
            if item["id"] not in nodes and (max_depth is not None and child_depth >= max_depth):
                stub = FolderNode(id=item["id"], name=item.get("name", "Untitled"), depth=child_depth)
                nodes[item["id"]] = stub
        else:
            local_files += 1
            file_node = _item_to_file_node(item, depth=work.depth + 1)
            children_map[work.folder_id].append(file_node)

    if _tracker:
        _tracker.update(local_folders, local_files)


async def traverse(
    connector: AbstractConnector,
    folder_id: str,
    folder_name: str | None = None,
    depth: int = 0,
    max_depth: int | None = None,
    _progress: Progress | None = None,
    _task_id: int | None = None,
    _tracker: Any = None,
) -> FolderNode:
    """
    Iterative BFS traversal of a Drive folder tree.

    Unlike the previous recursive implementation this version:
    - Uses a work queue (BFS) instead of call-stack recursion.
    - Bounds concurrency to ``MAX_CONCURRENT`` parallel API calls via
      an ``asyncio.Semaphore``, preventing thread-pool exhaustion.
    - Is safe for arbitrarily large Drive hierarchies.

    Stats are accumulated correctly by wiring child→parent in reverse
    BFS order (deepest nodes first), so ``add_child`` always sees the
    child's already-totalled sizes before the parent reads them.
    """
    if folder_name is None:
        folder_name = await connector.get_folder_name(folder_id)

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    queue: asyncio.Queue[_FolderWork] = asyncio.Queue()
    nodes: dict[str, FolderNode] = {}
    # Maps folder_id → ordered list of (child folder_id | FileNode)
    children_map: defaultdict[str, list] = defaultdict(list)
    # BFS visit order — used for bottom-up wiring in post-processing.
    visit_order: list[str] = []

    root_work = _FolderWork(
        folder_id=folder_id,
        folder_name=folder_name,
        depth=depth,
        parent_id=None,
    )
    await queue.put(root_work)

    # BFS loop: drain the queue level by level using bounded concurrency.
    pending: set[asyncio.Task] = set()

    while not queue.empty() or pending:
        # Drain the queue into tasks.
        while not queue.empty():
            work = await queue.get()
            visit_order.append(work.folder_id)
            task = asyncio.create_task(
                _fetch_folder(
                    connector=connector,
                    work=work,
                    sem=sem,
                    progress=_progress,
                    task_id=_task_id,
                    max_depth=max_depth,
                    queue=queue,
                    nodes=nodes,
                    children_map=children_map,
                    _tracker=_tracker,
                )
            )
            pending.add(task)
            # NOTE: do NOT use add_done_callback(pending.discard) here.
            # If we discard from the callback, the task is removed from `pending`
            # before asyncio.wait can return it in `done`, so its exception is
            # never retrieved ("Task exception was never retrieved" warning).

        if pending:
            # Wait for at least one task to finish before checking the queue again.
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            # Re-raise any exceptions from completed tasks immediately.
            for t in done:
                t.result()  # Raises if the task failed.


    # Post-processing: wire up parent → child in *reverse* BFS order so that
    # leaf nodes are fully populated before their parents call add_child and
    # read the accumulated totals.
    for parent_id in reversed(visit_order):
        parent_node = nodes.get(parent_id)
        if parent_node is None:
            continue
        for ref in children_map[parent_id]:
            if isinstance(ref, str):
                child_node = nodes.get(ref)
                if child_node is not None:
                    parent_node.add_child(child_node)
            else:
                # FileNode — order among files within a folder doesn't matter.
                parent_node.add_child(ref)

    return nodes[folder_id]


async def build_storage_tree(
    connector: AbstractConnector,
    root_id: str = "root",
    max_depth: int | None = None,
) -> StorageTree:
    """
    Build a complete StorageTree starting from ``root_id``.

    Wraps ``traverse`` with a Rich progress indicator and computes
    top-level stats for the returned StorageTree.
    """
    root_name = await connector.get_folder_name(root_id)

    console.print(f"\n[bold cyan]🔍 Scanning:[/bold cyan] [white]{root_name}[/white]")
    console.print("[dim]⏳ Note: Scanning large storage sources may take several minutes depending on depth and item count.[/dim]\n")

    import time
    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn("[blue]({task.fields[folders]:,} folders, {task.fields[files]:,} files)"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(
            "Traversing folders…", 
            total=None,
            folders=0,
            files=0
        )
        
        # We need a small class to track progress between threads/tasks
        class StatsTracker:
            folders = 0
            files = 0
            
            def update(self, folders: int, files: int):
                self.folders += folders
                self.files += files
                progress.update(task_id, folders=self.folders, files=self.files)

        tracker = StatsTracker()

        tree = await traverse(
            connector=connector,
            folder_id=root_id,
            folder_name=root_name,
            depth=0,
            max_depth=max_depth,
            _progress=progress,
            _task_id=task_id,
            _tracker=tracker,
        )
        
        duration = time.perf_counter() - start_time
        final_folders = tracker.folders
        final_files = tracker.files
        
        progress.update(task_id, description="Done ✅")

    # Print a clean summary of the scan results
    total_items = final_folders + final_files
    avg_per_sec = total_items / duration if duration > 0 else 0
    
    console.print(
        f"[bold green]✨ Scan complete![/bold green] "
        f"[dim]Processed [bold]{final_folders:,}[/bold] folders and "
        f"[bold]{final_files:,}[/bold] files in [bold]{duration:.1f}s[/bold] "
        f"([bold]{avg_per_sec:,.0f}[/bold] items/s)[/dim]\n"
    )

    # Count folders (depth-first).
    total_folders = _count_folders(tree)

    return StorageTree(
        root_id=root_id,
        root_name=root_name,
        tree=tree,
        total_files=tree.total_file_count,
        total_folders=total_folders,
        total_size_bytes=tree.total_size_bytes,
        max_depth_reached=_max_depth(tree),
    )


def _count_folders(node: FolderNode) -> int:
    """Recursively count all FolderNode instances in the tree."""
    count = 1  # Count self.
    for child in node.children:
        if isinstance(child, FolderNode):
            count += _count_folders(child)
    return count


def _max_depth(node: FolderNode, current: int = 0) -> int:
    """Return the maximum depth reached in the tree."""
    max_d = current
    for child in node.children:
        if isinstance(child, FolderNode):
            max_d = max(max_d, _max_depth(child, current + 1))
    return max_d
