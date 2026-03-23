"""docto-trace-storage: Deep storage auditing for Google Drive."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("docto-trace-storage")
except PackageNotFoundError:
    # Fallback when running directly from source without pip install.
    __version__ = "0.2.0"

__author__ = "Docto Studio"
