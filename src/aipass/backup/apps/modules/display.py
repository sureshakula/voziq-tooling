# =================== AIPass ====================
# Name: display.py
# Description: Rich CLI rendering for backup results (full 9-stage output)
# Version: 2.0.0
# Created: 2026-06-12
# Modified: 2026-06-12
# =============================================

"""Rich CLI rendering for backup — full output pipeline faithfully ported from gold source."""

from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from aipass.prax import logger
from aipass.cli.apps.modules import console, error, header, success, warning

from aipass.backup.apps.handlers.json import json_handler
from aipass.backup.apps.handlers.report.formatter import _human_bytes
from aipass.backup.apps.handlers.report.result import BackupResult
from aipass.backup.apps.handlers.state.backup_timestamps import (
    format_age,
    get_timestamps,
    update_timestamp,
)

MODULE_NAME = "display"


def print_introspection():
    """Display module info."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print("  Rich CLI rendering for backup results (full 9-stage output)")
    console.print("  Not a command module — used by snapshot/versioned/all")


def show_last_backups() -> None:
    """Stage 1: Show 'Last backups:' panel with dim ages."""
    ts = get_timestamps()
    console.print()
    console.print("[dim]Last backups:[/dim]")
    console.print(f"  [dim]Snapshot:   {format_age(ts.get('snapshot'))}[/dim]")
    console.print(f"  [dim]Versioned:  {format_age(ts.get('versioned'))}[/dim]")
    console.print(f"  [dim]Drive sync: {format_age(ts.get('drive_sync'))}[/dim]")


def show_run_header(result: BackupResult) -> None:
    """Stage 3: Show run header with boxed panel."""
    header(
        f"Backup — {result.mode.title()}",
        {
            "Project": result.project_root,
            "Mode": result.mode,
        },
    )


def create_progress_bar():
    """Stage 5: Create and return a Rich Progress context for the copy loop."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


def show_result_summary(result: BackupResult) -> None:
    """Stage 6+7: Show rich result summary (stats + completion status)."""
    console.print()

    if result.errors:
        if len(result.errors) > 5:
            error(
                f"{result.mode.title()} backup FAILED",
                suggestion="Check file permissions and disk space",
            )
        else:
            warning(
                f"{result.mode.title()} completed with {len(result.errors)} errors",
                details="; ".join(result.errors[:3]),
            )
        for err in result.errors[:5]:
            console.print(f"  [dim]- {err}[/dim]")
        if len(result.errors) > 5:
            console.print(f"  [dim]... and {len(result.errors) - 5} more[/dim]")
    else:
        success(
            f"{result.mode.title()} backup complete",
            files_copied=result.files_copied,
            files_checked=result.files_checked,
            files_skipped=result.files_skipped,
            size=_human_bytes(result.bytes_copied),
        )

    location = result.backup_path if result.backup_path else result.project_root
    console.print(f"  [dim]Duration: {result.duration_seconds:.1f}s | Location: {location}[/dim]")

    json_handler.log_operation("render_result", {"mode": result.mode})
    logger.info(f"[backup] Rendered {result.mode} result: {result.files_copied} files")


def show_backups_now(mode: str) -> None:
    """Stage 8: Update timestamp and show 'Backups now:' panel with updated dim ages."""
    update_timestamp(mode)
    ts = get_timestamps()
    console.print()
    console.print("[dim]Backups now:[/dim]")
    console.print(f"  [dim]Snapshot:   {format_age(ts.get('snapshot'))}[/dim]")
    console.print(f"  [dim]Versioned:  {format_age(ts.get('versioned'))}[/dim]")
    console.print(f"  [dim]Drive sync: {format_age(ts.get('drive_sync'))}[/dim]")


# =============================================
