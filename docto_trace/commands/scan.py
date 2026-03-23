"""
`docto-trace scan` command — the core MVP action.

Authenticates to Google Drive, traverses the folder tree,
runs analytics, writes report.json, and prints a Rich summary.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from docto_trace.auth.google_drive import build_drive_service
from docto_trace.config import settings
from docto_trace.connectors.google_drive import GoogleDriveConnector
from docto_trace.engine.analytics import build_insight_summary
from docto_trace.engine.auditor import build_audit_summary
from docto_trace.engine.traversal import build_storage_tree
from docto_trace.schemas.report import HealthReport, QuotaSummary

console = Console()
err_console = Console(stderr=True)


def scan(
    root_id: str = typer.Option(
        "root",
        "--root-id",
        "-r",
        help="Google Drive folder ID to start the scan from. Defaults to 'root' (My Drive).",
    ),
    max_depth: Optional[int] = typer.Option(  # noqa: UP007
        None,
        "--max-depth",
        "-d",
        help="Maximum folder depth to traverse. Omit for unlimited depth.",
    ),
    top_n: int = typer.Option(
        settings.top_n,
        "--top",
        "-n",
        help="Number of top-largest folders to include in the report.",
    ),
    deep_threshold: int = typer.Option(
        settings.deep_folder_threshold,
        "--deep-threshold",
        help="Nesting depth at which a folder is flagged as 'deep'.",
    ),
    credentials: Path = typer.Option(
        settings.credentials_path,
        "--credentials",
        "-c",
        help="Path to the OAuth2 credentials JSON file.",
    ),
    output_dir: Path = typer.Option(
        settings.output_dir,
        "--output",
        "-o",
        help="Directory where report.json is written.",
    ),
    service_account: Optional[Path] = typer.Option(  # noqa: UP007
        None,
        "--service-account",
        "-s",
        help="Path to a service account key JSON (skips OAuth2 browser flow).",
    ),
    stale_threshold: int = typer.Option(
        settings.stale_threshold_months,
        "--stale-threshold",
        "-S",
        help="Months without modification before a file is flagged as a zombie.",
    ),
    llm_model: Optional[str] = typer.Option(  # noqa: UP007
        settings.llm_model,
        "--llm-model",
        help="LiteLLM compatible model string for AI Readiness qualitative report.",
    ),
    open_ui: bool = typer.Option(
        True,
        "--ui/--no-ui",
        help="Automatically launch the Streamlit UI after scanning.",
    ),
    agent_iterations: int = typer.Option(
        30,
        "--agent-iterations",
        help="Maximum loops the Autonomous Agent will perform before terminating.",
    ),
) -> None:
    """
    Scan Google Drive and generate a structural health report.

    \b
    Examples:
      docto-trace scan
      docto-trace scan --root-id 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
      docto-trace scan --max-depth 5 --top 20 --output ./reports/
    """
    try:
        # 1. Authenticate
        err_console.print("[bold]🔐 Authenticating with Google Drive…[/bold]")
        service = build_drive_service(
            credentials_path=credentials,
            token_path=settings.token_path,
            service_account_path=service_account,
        )

        # 2. Create connector
        connector = GoogleDriveConnector(service=service, page_size=settings.page_size)

        # 3. Traverse the Drive tree (async)
        storage_tree = asyncio.run(
            build_storage_tree(
                connector=connector,
                root_id=root_id,
                max_depth=max_depth,
            )
        )

        # 4. Run Phase 1 analytics
        err_console.print("[bold]📊 Running analytics…[/bold]")
        insights = build_insight_summary(
            tree=storage_tree,
            top_n=top_n,
            deep_folder_threshold=deep_threshold,
        )

        # 5. Run Phase 2 audits (zombie detection + deduplication)
        err_console.print("[bold]🔍 Running audits…[/bold]")
        zombies, duplicates, action_plan = build_audit_summary(
            tree=storage_tree,
            stale_threshold_months=stale_threshold,
        )

        # 5.5. Run Phase 4 AI Readiness
        err_console.print("[bold]🤖 Calculating AI Readiness…[/bold]")
        from docto_trace.engine.ai_readiness import build_ai_readiness_summary
        ai_readiness = build_ai_readiness_summary(
            tree=storage_tree,
            llm_model=llm_model,
            max_agent_iterations=agent_iterations,
        )

        # 6. Fetch account-wide quota (Drive + Gmail + Photos)
        err_console.print("[bold]📦 Fetching account quota…[/bold]")
        quota: QuotaSummary | None = None
        try:
            raw_quota = asyncio.run(connector.get_quota())
            drive_b  = raw_quota["usageInDrive"]
            total_b  = raw_quota["usage"]
            trash_b  = raw_quota["usageInDriveTrash"]
            limit_b  = raw_quota["limit"]
            quota = QuotaSummary(
                total_bytes=total_b,
                drive_bytes=drive_b,
                trash_bytes=trash_b,
                other_bytes=max(0, total_b - drive_b),
                limit_bytes=limit_b,
            )
        except Exception as exc:  # noqa: BLE001
            err_console.print(f"[yellow]⚠️  Could not fetch account quota: {exc}[/yellow]")

        # 7. Build HealthReport
        report = HealthReport(
            storage_tree=storage_tree,
            quota=quota,
            insights=insights,
            zombies=zombies,
            duplicates=duplicates,
            action_plan=action_plan,
            ai_readiness=ai_readiness,
        )

        # 7. Write report.json
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "report.json"
        report_path.write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )

        # 8. Print summary to terminal
        _print_summary(report, report_path)

        if open_ui:
            console.print("\n[bold green]🚀 Transitioning to interactive UI...[/bold green]")
            from docto_trace.commands.ui import ui as launch_ui
            launch_ui(report_json=report_path)

    except FileNotFoundError as exc:
        err_console.print(f"\n[bold red]❌ Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        err_console.print(f"\n[bold red]❌ Unexpected error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# Rich output helpers
# ---------------------------------------------------------------------------


def _print_summary(report: HealthReport, report_path: Path) -> None:
    """Print a formatted summary table to stdout."""
    tree = report.storage_tree
    insights = report.insights

    console.print()
    console.rule("[bold cyan]📦 Storage Overview[/bold cyan]")
    console.print(f"  [bold]Root:[/bold]          {tree.root_name}")
    console.print(f"  [bold]Total files:[/bold]   {tree.total_files:,}")
    console.print(f"  [bold]Total folders:[/bold] {tree.total_folders:,}")
    console.print(f"  [bold]Total size:[/bold]    {_fmt_bytes(tree.total_size_bytes)}")
    console.print(f"  [bold]Max depth:[/bold]     {tree.max_depth_reached}")
    console.print(f"  [bold]Scanned at:[/bold]    {tree.scanned_at.isoformat()}")

    # Show account-wide quota if available
    if report.quota is not None:
        q = report.quota
        console.print()
        console.rule("[bold cyan]☁️  Google Account Quota[/bold cyan]")
        used_pct = (
            f" ({q.total_bytes / q.limit_bytes * 100:.1f}% of {_fmt_bytes(q.limit_bytes)})"
            if q.limit_bytes > 0
            else ""
        )
        console.print(f"  [bold]Total used:[/bold]    {_fmt_bytes(q.total_bytes)}{used_pct}")
        console.print(f"  [bold]My Drive:[/bold]      {_fmt_bytes(q.drive_bytes)}")
        if q.trash_bytes > 0:
            console.print(f"  [bold]Trash:[/bold]         {_fmt_bytes(q.trash_bytes)}")
        console.print(f"  [bold]Gmail + Photos:[/bold] {_fmt_bytes(q.other_bytes)}")
        gap = q.drive_bytes - tree.total_size_bytes
        if gap > 0:
            console.print(
                f"  [dim]↳ {_fmt_bytes(gap)} in Drive not captured by scan "
                "(Google-native files, shortcuts, items outside scan root)[/dim]"
            )
    console.print()

    # Top folders table
    if insights.top_folders:
        console.rule(f"[bold yellow]🏆 Top {insights.top_n} Largest Folders[/bold yellow]")
        table = Table(
            "Rank", "Folder", "Path", "Files", "Size",
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
        )
        for i, folder in enumerate(insights.top_folders, start=1):
            table.add_row(
                str(i),
                folder.name,
                folder.path,
                f"{folder.file_count:,}",
                folder.total_size_human,
            )
        console.print(table)
        console.print()

    # Deep folders table
    if insights.deep_folders:
        console.rule(
            f"[bold red]🕳️  Deep Folders (depth ≥ {insights.deep_folder_threshold})[/bold red]"
        )
        deep_table = Table(
            "Folder", "Path", "Depth", "Files", "Size",
            show_header=True,
            header_style="bold red",
            border_style="dim",
        )
        for folder in insights.deep_folders[:20]:  # Cap display at 20.
            deep_table.add_row(
                folder.name,
                folder.path,
                str(folder.depth),
                f"{folder.file_count:,}",
                folder.total_size_human,
            )
        console.print(deep_table)
        console.print()
    else:
        console.print(
            f"[green]✅ No deep folders found (threshold = {insights.deep_folder_threshold}).[/green]\n"
        )

    # Zombie files table
    if report.zombies:
        console.rule(
            f"[bold yellow]🧟 Zombie Files ({len(report.zombies)} stale)[/bold yellow]"
        )
        zombie_table = Table(
            "File", "Path", "Last Modified", "Size",
            show_header=True,
            header_style="bold yellow",
            border_style="dim",
        )
        for z in report.zombies[:30]:  # Cap display at 30.
            modified_str = z.last_modified.strftime("%Y-%m-%d") if z.last_modified else "Unknown"
            zombie_table.add_row(
                z.name,
                z.path,
                modified_str,
                _fmt_bytes(z.size_bytes),
            )
        console.print(zombie_table)
        if len(report.zombies) > 30:
            console.print(
                f"  [dim]… and {len(report.zombies) - 30} more. See report.json for full list.[/dim]"
            )
        console.print()
    else:
        console.print("[green]✅ No zombie files detected.[/green]\n")

    # Duplicate groups table
    if report.duplicates:
        total_wasted = sum(d.wasted_bytes for d in report.duplicates)
        console.rule(
            f"[bold magenta]♻️  Duplicate Groups "
            f"({len(report.duplicates)} groups · {_fmt_bytes(total_wasted)} wasted)[/bold magenta]"
        )
        dup_table = Table(
            "Fingerprint", "Path", "Size/copy", "Wasted",
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
            show_lines=True,  # Horizontal rules between rows aid readability.
        )
        for d in report.duplicates[:20]:  # Cap display at 20 groups.
            short_fp = d.fingerprint[:16] + "…" if len(d.fingerprint) > 16 else d.fingerprint
            # Build a multi-line cell: one path per copy.
            paths_cell = "\n".join(
                _truncate(p, 70) for p in d.file_paths
            ) or "—"
            dup_table.add_row(
                f"{short_fp}\n[dim]({len(d.files)} copies)[/dim]",
                paths_cell,
                _fmt_bytes(d.size_bytes_per_copy),
                f"[bold]{_fmt_bytes(d.wasted_bytes)}[/bold]",
            )
        console.print(dup_table)
        if len(report.duplicates) > 20:
            console.print(
                f"  [dim]… and {len(report.duplicates) - 20} more. See report.json for full list.[/dim]"
            )
        console.print()
    else:
        console.print("[green]✅ No duplicate files detected.[/green]\n")

    # AI Readiness section
    if report.ai_readiness:
        ar = report.ai_readiness
        console.rule("[bold cyan]🤖 AI Readiness Score[/bold cyan]")
        console.print(f"  [bold]Naming Entropy:[/bold] {ar.naming_entropy_score}/100.0 (Higher is more descriptive)")
        
        total_f = ar.structured_files_count + ar.unstructured_files_count
        if total_f > 0:
            s_pct = (ar.structured_files_count / total_f) * 100
            u_pct = (ar.unstructured_files_count / total_f) * 100
            console.print(f"  [bold]Structured files:[/bold]   {ar.structured_files_count:,} ({s_pct:.1f}%) | {_fmt_bytes(ar.structured_bytes)}")
            console.print(f"  [bold]Unstructured files:[/bold] {ar.unstructured_files_count:,} ({u_pct:.1f}%) | {_fmt_bytes(ar.unstructured_bytes)}")
        
        if ar.ai_analysis_report:
            console.print("\n  [bold cyan]LLM Analysis & Action Plan:[/bold cyan]")
            from rich.panel import Panel
            console.print(Panel(ar.ai_analysis_report, border_style="cyan", padding=(1, 2)))
        console.print()

    console.rule("[bold green]✅ Report saved[/bold green]")
    console.print(f"  [bold]Output:[/bold] {report_path.resolve()}")
    console.print()



def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} PB"


def _truncate(text: str, max_len: int) -> str:
    """Truncate a string with a middle ellipsis to keep both ends visible."""
    if len(text) <= max_len:
        return text
    half = (max_len - 1) // 2
    return f"{text[:half]}…{text[-half:]}"
