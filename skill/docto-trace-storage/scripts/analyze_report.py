#!/usr/bin/env python3
"""
analyze_report.py — Convert a report.json into a compact, LLM-ready context block.

Called by Claude after run_scan.py produces the report. Large reports can have
thousands of files; this script condenses them to fit within context windows.

Usage:
  python analyze_report.py /path/to/output/report.json [--max-zombies N] [--max-dupes N]

Output: structured markdown printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} PB"


def _months_ago(iso_str: str | None) -> str:
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        months = (now.year - dt.year) * 12 + (now.month - dt.month)
        return f"{months} months ago ({dt.strftime('%Y-%m-%d')})"
    except Exception:
        return iso_str


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_overview(report: dict) -> str:
    tree = report.get("storage_tree", {})
    lines = [
        "## 📦 Storage Overview",
        f"- **Root**: {tree.get('root_name', 'My Drive')}",
        f"- **Total files**: {tree.get('total_files', 0):,}",
        f"- **Total folders**: {tree.get('total_folders', 0):,}",
        f"- **Total size**: {_fmt_bytes(tree.get('total_size_bytes', 0))}",
        f"- **Max depth reached**: {tree.get('max_depth_reached', 0)}",
        f"- **Scanned at**: {tree.get('scanned_at', report.get('generated_at', 'unknown'))}",
        f"- **Schema version**: {report.get('schema_version', 'unknown')}",
    ]
    return "\n".join(lines)


def render_top_folders(report: dict, limit: int = 15) -> str:
    folders = report.get("insights", {}).get("top_folders", [])
    if not folders:
        return "## 🏆 Top Folders\nNone found."
    lines = ["## 🏆 Top Largest Folders", "| Rank | Name | Path | Files | Size |",
             "|---|---|---|---|---|"]
    for i, f in enumerate(folders[:limit], 1):
        lines.append(
            f"| {i} | {f.get('name','')} | {f.get('path','')} "
            f"| {f.get('file_count',0):,} | {f.get('total_size_human','')} |"
        )
    return "\n".join(lines)


def render_zombies(report: dict, limit: int = 20) -> str:
    zombies = report.get("zombies", [])
    total = len(zombies)
    if not total:
        return "## 🧟 Zombie Files\nNo zombie files detected. ✅"

    total_bytes = sum(z.get("size_bytes", 0) for z in zombies)
    lines = [
        f"## 🧟 Zombie Files — {total:,} stale files ({_fmt_bytes(total_bytes)} total)",
        "| Name | Path | Last Modified | Size |",
        "|---|---|---|---|",
    ]
    for z in sorted(zombies, key=lambda x: x.get("last_modified") or "", reverse=False)[:limit]:
        lines.append(
            f"| {z.get('name','')} | {z.get('path','')} "
            f"| {_months_ago(z.get('last_modified'))} | {_fmt_bytes(z.get('size_bytes',0))} |"
        )
    if total > limit:
        lines.append(f"\n_… and {total - limit} more. See report.json for the full list._")
    return "\n".join(lines)


def render_duplicates(report: dict, limit: int = 15) -> str:
    dupes = report.get("duplicates", [])
    total = len(dupes)
    if not total:
        return "## ♻️ Duplicate Files\nNo duplicates detected. ✅"

    total_wasted = sum(d.get("wasted_bytes", 0) for d in dupes)
    lines = [
        f"## ♻️ Duplicate Groups — {total:,} groups ({_fmt_bytes(total_wasted)} wasted)",
        "| Fingerprint | Copies | Paths | Wasted |",
        "|---|---|---|---|",
    ]
    for d in sorted(dupes, key=lambda x: x.get("wasted_bytes", 0), reverse=True)[:limit]:
        fp = d.get("fingerprint", "")[:16] + "…"
        paths = " · ".join(d.get("file_paths", [])[:3])
        if len(d.get("file_paths", [])) > 3:
            paths += f" (+{len(d['file_paths']) - 3} more)"
        lines.append(
            f"| `{fp}` | {len(d.get('files', []))} | {paths} "
            f"| **{_fmt_bytes(d.get('wasted_bytes', 0))}** |"
        )
    if total > limit:
        lines.append(f"\n_… and {total - limit} more groups. See report.json for the full list._")
    return "\n".join(lines)


def render_action_plan(report: dict) -> str:
    plan = report.get("action_plan", [])
    if not plan:
        return "## ✅ Action Plan\nNo actions recommended."

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_plan = sorted(plan, key=lambda x: severity_order.get(x.get("severity", "info"), 2))

    icons = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    lines = [f"## 📋 Action Plan ({len(plan)} items)"]
    for item in sorted_plan:
        sev = item.get("severity", "info")
        icon = icons.get(sev, "⚪")
        cat = item.get("category", "").capitalize()
        desc = item.get("description", "")
        lines.append(f"- {icon} **[{sev.upper()} / {cat}]** {desc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Condense a report.json into a Claude-friendly context block."
    )
    parser.add_argument("report_path", help="Path to the report.json file.")
    parser.add_argument("--max-zombies", type=int, default=20,
                        help="Max zombie rows to include (default: 20).")
    parser.add_argument("--max-dupes", type=int, default=15,
                        help="Max duplicate groups to include (default: 15).")
    args = parser.parse_args()

    path = Path(args.report_path)
    if not path.exists():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        return 1

    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {path}: {e}", file=sys.stderr)
        return 1

    sections = [
        f"# Docto Trace — Storage Audit Report\n_Source: `{path.resolve()}`_\n",
        render_overview(report),
        render_top_folders(report),
        render_zombies(report, limit=args.max_zombies),
        render_duplicates(report, limit=args.max_dupes),
        render_action_plan(report),
    ]

    print("\n\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
