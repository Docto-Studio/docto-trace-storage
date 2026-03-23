"""Abstract base connector interface for cloud storage providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractConnector(ABC):
    """
    Protocol that every cloud storage connector must implement.

    Connectors are responsible for fetching raw item metadata from
    their respective cloud provider. They do NOT build the tree;
    that is the engine's responsibility.
    """

    @abstractmethod
    async def list_items(self, folder_id: str) -> list[dict]:
        """
        Return a flat list of raw item dicts for the given folder_id.

        Each dict must contain at minimum:
          - ``id``        (str)  — Provider's unique file/folder identifier.
          - ``name``      (str)  — Display name.
          - ``mimeType``  (str)  — MIME type. Folders use a provider-specific value.
          - ``size``      (str, optional) — File size in bytes as a string.
          - ``createdTime``  (str, optional) — ISO 8601 datetime string.
          - ``modifiedTime`` (str, optional) — ISO 8601 datetime string.
          - ``parents``   (list[str], optional) — Parent folder IDs.
          - ``owners``    (list[dict], optional) — Owner info dicts.
          - ``webViewLink`` (str, optional) — Browser-accessible URL.
        """
        ...

    @abstractmethod
    async def get_folder_name(self, folder_id: str) -> str:
        """
        Return the display name of a folder given its ID.

        Used to populate the root folder name in the StorageTree.
        """
        ...
