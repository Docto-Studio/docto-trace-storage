"""Local File System connector — fast, cross-platform directory traversal."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from datetime import datetime

from docto_trace.connectors.base import AbstractConnector

# Folder MIME type constant for local consistency
LOCAL_FOLDER_MIME = "application/x-directory"

# Common "black hole" folders to ignore by default for performance and relevance
DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", ".venv", "__pycache__", 
    ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "bin", "obj" # For .NET devs
}
DEFAULT_IGNORE_FILES = {".DS_Store", "Thumbs.db"}


class LocalFileSystemConnector(AbstractConnector):
    """
    Connector for the local file system.

    Implements the AbstractConnector interface by mapping OS file metadata
    to the common dictionary format expected by the traversal engine.
    """

    def __init__(self, skip_hidden: bool = True) -> None:
        self.skip_hidden = skip_hidden

    async def list_items(self, folder_id: str) -> list[dict]:
        """
        Return metadata for all items directly inside the local ``folder_id`` (path).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_items_sync, folder_id)

    def _list_items_sync(self, folder_path: str) -> list[dict]:
        """Synchronous implementation using os.scandir for performance."""
        items = []
        try:
            with os.scandir(folder_path) as it:
                for entry in it:
                    name = entry.name
                    
                    # 1. Skip hidden if requested
                    if self.skip_hidden and name.startswith(".") and name not in [".", ".."]:
                        if name not in [".env"]: # Exception for important config
                            continue
                            
                    # 2. Skip common black holes
                    if entry.is_dir() and name in DEFAULT_IGNORE_DIRS:
                        continue
                    if entry.is_file() and name in DEFAULT_IGNORE_FILES:
                        continue

                    try:
                        stat = entry.stat(follow_symlinks=False)
                        
                        # Map to the common dict format
                        item = {
                            "id": entry.path,
                            "name": entry.name,
                            "mimeType": LOCAL_FOLDER_MIME if entry.is_dir() else "application/octet-stream",
                            "size": str(stat.st_size),
                            "createdTime": datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z",
                            "modifiedTime": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z",
                            "parents": [folder_path],
                        }
                        
                        # Add MD5 for files if small enough (optional optimization)
                        # For now, we skip MD5 here to maintain parity with Drive's fast listing
                        
                        items.append(item)
                    except (PermissionError, OSError):
                        # Skip files we can't access
                        continue
        except (PermissionError, OSError):
            # Skip folders we can't access
            pass
            
        return items

    async def get_folder_name(self, folder_id: str) -> str:
        """Return the absolute path or 'Root' if at system root."""
        path = Path(folder_id).absolute()
        if folder_id == os.path.abspath(os.sep):
            return "System Root"
        return path.name if path.name else str(path)

    async def get_quota(self, path: str = ".") -> dict:
        """
        Fetch disk usage for the partition containing the given path.
        """
        loop = asyncio.get_event_loop()
        usage = await loop.run_in_executor(None, shutil.disk_usage, path)
        return {
            "usage": usage.used,
            "usageInDrive": usage.used, # Mapping 'Drive' to 'Local Partition'
            "usageInDriveTrash": 0,     # Trash detection varies by OS, keeping it 0 for now
            "limit": usage.total,
        }

    def get_folder_mime(self) -> str:
        """Return the local directory MIME type."""
        return LOCAL_FOLDER_MIME
