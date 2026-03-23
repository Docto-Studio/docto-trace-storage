#!/usr/bin/env python3
"""
run_scan.py — Active invocation bridge for the Docto Trace Skill.

This script invokes `docto-trace scan` as a subprocess, forwarding all
flags transparently. Called by Claude when the user requests a Drive audit.

The CLI itself is NOT modified — this script is purely delegation.

Usage (by Claude):
  python run_scan.py [--root-id ID] [--max-depth N] [--top N]
                     [--stale-threshold MONTHS] [--output DIR]
                     [--credentials PATH] [--service-account PATH]

Exit codes:
  0 — success; last stdout line contains the path to report.json
  1 — error; stderr contains a human-readable error message
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Pre-flight: ensure docto-trace-storage is installed
# ---------------------------------------------------------------------------

def _ensure_installed() -> bool:
    """
    Try to import the package. If missing, install it via pip and retry.
    Returns True if the package is available after the check.
    """
    try:
        importlib.import_module("docto_trace")
        return True
    except ModuleNotFoundError:
        pass

    print("[docto-trace-skill] docto-trace-storage not found — installing via pip…", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "docto-trace-storage>=0.2.0"],
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            "\n[ERROR] pip install failed. Please install manually:\n"
            "  pip install docto-trace-storage\n",
            file=sys.stderr,
        )
        return False

    # Invalidate import caches so the freshly installed package is discoverable.
    importlib.invalidate_caches()
    try:
        importlib.import_module("docto_trace")
        print("[docto-trace-skill] Installation successful.", flush=True)
        return True
    except ModuleNotFoundError:
        print(
            "\n[ERROR] Package installed but module still not importable. "
            "Check your Python environment.\n",
            file=sys.stderr,
        )
        return False


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Invoke docto-trace scan and return path to report.json",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--root-id", "-r", default="root",
                   help="Google Drive folder ID to scan from (default: My Drive root).")
    p.add_argument("--max-depth", "-d", type=int, default=None,
                   help="Max folder depth to traverse (default: unlimited).")
    p.add_argument("--top", "-n", type=int, default=10,
                   help="Top-N largest folders to include in the report.")
    p.add_argument("--deep-threshold", type=int, default=5,
                   help="Nesting depth at which a folder is flagged as 'deep'.")
    p.add_argument("--stale-threshold", "-S", type=int, default=24,
                   help="Months without modification before a file is flagged zombie.")
    p.add_argument("--output", "-o", default="output",
                   help="Directory where report.json will be written.")
    p.add_argument("--credentials", "-c", default=None,
                   help="Path to OAuth2 credentials JSON (optional; uses bundled by default).")
    p.add_argument("--service-account", "-s", default=None,
                   help="Path to a service account key JSON (skips browser OAuth flow).")
    return p


def build_cmd(args: argparse.Namespace) -> list[str]:
    """
    Build the subprocess command using `sys.executable -m docto_trace.cli scan`.

    Using the module invocation (instead of the `docto-trace` entrypoint) ensures
    the command works in any environment — including Skill sandboxes where the
    entrypoint script may not be on PATH.
    """
    cmd: list[str] = [sys.executable, "-m", "docto_trace.cli", "scan"]

    cmd += ["--root-id", args.root_id]
    cmd += ["--top", str(args.top)]
    cmd += ["--deep-threshold", str(args.deep_threshold)]
    cmd += ["--stale-threshold", str(args.stale_threshold)]
    cmd += ["--output", str(args.output)]

    if args.max_depth is not None:
        cmd += ["--max-depth", str(args.max_depth)]
    if args.credentials:
        cmd += ["--credentials", args.credentials]
    if args.service_account:
        cmd += ["--service-account", args.service_account]

    return cmd


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Step 1 — ensure the package is available (auto-installs if missing).
    if not _ensure_installed():
        return 1

    # Step 2 — build and run the scan command.
    cmd = build_cmd(args)
    print(f"[docto-trace-skill] Running: {' '.join(cmd)}", flush=True)

    result = subprocess.run(cmd, text=True, check=False)

    if result.returncode != 0:
        print(
            f"\n[ERROR] docto-trace scan exited with code {result.returncode}.\n"
            "Possible causes:\n"
            "  • Not authenticated — run: docto-trace login\n"
            "  • Invalid credentials path — check --credentials flag\n"
            "  • Network issue — verify internet connectivity\n",
            file=sys.stderr,
        )
        return result.returncode

    # Step 3 — resolve and print the report path for Claude to capture.
    report_path = Path(args.output) / "report.json"
    print(f"\n[docto-trace-skill] Report generated at: {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
