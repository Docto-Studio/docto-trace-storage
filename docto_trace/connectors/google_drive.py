"""Google Drive connector — async, paginated, with exponential back-off."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import httplib2
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from rich.console import Console

from docto_trace.connectors.base import AbstractConnector

console = Console(stderr=True)

# Fields to request from the Drive API — only what we need to minimize payload.
_FIELDS = (
    "nextPageToken, "
    "files(id, name, mimeType, size, quotaBytesUsed, createdTime, modifiedTime, "
    "parents, owners(emailAddress), webViewLink, trashed, md5Checksum)"
)

FOLDER_MIME = "application/vnd.google-apps.folder"

# Socket timeout for each thread-local Http instance (seconds).
# httplib2.Http is NOT thread-safe — sharing one instance across concurrent
# thread-pool workers causes socket corruption that manifests as TimeoutError.
# We solve this by giving each thread its own Http instance via threading.local().
_SOCKET_TIMEOUT = 120

# Thread-local storage — each worker thread gets its own AuthorizedHttp.
_thread_local = threading.local()


def _get_thread_local_http(creds: Any) -> AuthorizedHttp:
    """
    Return a per-thread ``AuthorizedHttp`` instance backed by its own
    ``httplib2.Http`` connection pool.

    ``httplib2.Http`` maintains internal connection state (keep-alive sockets,
    caches) that is **not safe to share across threads**.  Calling
    ``request.execute()`` from multiple threads on the same ``Http`` object
    causes socket reads to interleave, producing spurious ``TimeoutError`` and
    "Task exception was never retrieved" warnings.

    Using ``threading.local`` ensures each OS thread gets a fresh, isolated
    ``Http`` instance for the lifetime of that thread.
    """
    if not hasattr(_thread_local, "http"):
        _thread_local.http = AuthorizedHttp(
            creds, http=httplib2.Http(timeout=_SOCKET_TIMEOUT)
        )
    return _thread_local.http  # type: ignore[return-value]


class GoogleDriveConnector(AbstractConnector):
    """
    Async Google Drive connector built on top of the synchronous
    ``googleapiclient`` library (which does not support asyncio natively).

    Strategy: run each blocking API call in a thread-pool executor so the
    ``asyncio`` event loop remains unblocked during network I/O.

    Thread-safety: every worker thread gets its own ``AuthorizedHttp`` +
    ``httplib2.Http`` via ``threading.local``.  The Drive ``Resource`` object
    itself (``self._service``) is only used to *build* request objects, which
    is safe to do from multiple threads; the actual I/O is done through
    per-thread http instances injected via ``request.execute(http=...)``.
    """

    def __init__(self, service: Resource, page_size: int = 1000) -> None:
        self._service = service
        self._page_size = min(page_size, 1000)  # Drive hard-caps at 1000.

        # Extract credentials from the service so we can create per-thread
        # http instances.  ``service._http`` is the AuthorizedHttp built by
        # ``googleapiclient.discovery.build``; ``.credentials`` is the
        # underlying google-auth Credentials object.
        try:
            self._creds: Any = service._http.credentials  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback: no credentials found (e.g. mocked service in tests).
            # Fall back to the service's shared http — fine in single-thread tests.
            self._creds = None

    # ------------------------------------------------------------------
    # Public interface (AbstractConnector)
    # ------------------------------------------------------------------

    async def list_items(self, folder_id: str) -> list[dict]:
        """
        Return all non-trashed items directly inside ``folder_id``.

        Pages through the Drive API automatically and returns a single
        flat list. Applies exponential back-off on 429/403/503 errors.
        """
        all_items: list[dict] = []
        page_token: str | None = None

        while True:
            items, page_token = await self._fetch_page(folder_id, page_token)
            all_items.extend(items)
            if not page_token:
                break

        return all_items

    async def get_folder_name(self, folder_id: str) -> str:
        """Return the display name of the given folder ID."""
        if folder_id == "root":
            return "My Drive"
        loop = asyncio.get_event_loop()
        http = _get_thread_local_http(self._creds) if self._creds is not None else None
        meta = await loop.run_in_executor(
            None,
            lambda: self._service.files()
            .get(fileId=folder_id, fields="name", supportsAllDrives=True)
            .execute(http=http),
        )
        return meta.get("name", folder_id)

    async def get_quota(self) -> dict:
        """
        Fetch the Google account storage quota via Drive about.get().

        Returns a dict with keys: usage, usageInDrive, usageInDriveTrash, limit.
        All values are integers (bytes); limit is 0 if the account has unlimited quota.
        Requires only the drive.readonly scope (already granted).
        """
        loop = asyncio.get_event_loop()
        http = _get_thread_local_http(self._creds) if self._creds is not None else None
        about = await loop.run_in_executor(
            None,
            lambda: self._service.about()
            .get(fields="storageQuota")
            .execute(http=http),
        )
        quota = about.get("storageQuota", {})
        return {
            "usage":             int(quota.get("usage", 0)),
            "usageInDrive":      int(quota.get("usageInDrive", 0)),
            "usageInDriveTrash": int(quota.get("usageInDriveTrash", 0)),
            "limit":             int(quota.get("limit", 0)),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_page(
        self, folder_id: str, page_token: str | None
    ) -> tuple[list[dict], str | None]:
        """Fetch a single page of results with exponential back-off."""
        loop = asyncio.get_event_loop()
        max_retries = 5

        for attempt in range(max_retries):
            try:
                result = await loop.run_in_executor(
                    None, lambda: self._execute_list(folder_id, page_token)
                )
                files = [f for f in result.get("files", []) if not f.get("trashed")]
                return files, result.get("nextPageToken")

            except HttpError as exc:
                status = exc.resp.status
                if status in (429, 403, 503) and attempt < max_retries - 1:
                    wait = 2**attempt
                    console.print(
                        f"[yellow]⚠️  Rate limited (HTTP {status}). "
                        f"Retrying in {wait}s… (attempt {attempt + 1}/{max_retries})[/yellow]"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        return [], None  # Unreachable, but satisfies the type checker.

    def _execute_list(
        self, folder_id: str, page_token: str | None
    ) -> dict[str, Any]:
        """
        Build and execute the Drive files.list call (blocking).

        Passes a per-thread ``AuthorizedHttp`` to ``request.execute`` so that
        each thread-pool worker uses its own isolated connection pool, avoiding
        the ``TimeoutError`` caused by concurrent access to a shared
        ``httplib2.Http`` instance.
        """
        request = self._service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=self._page_size,
            fields=_FIELDS,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        http = _get_thread_local_http(self._creds) if self._creds is not None else None
        return request.execute(http=http)
