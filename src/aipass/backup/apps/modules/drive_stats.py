# =================== AIPass ====================
# Name: drive_stats.py
# Description: Drive stats module — shows file tracker statistics
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-06-12
# =============================================

"""Drive Stats Module — displays tracker statistics for a project."""

import sys

from aipass.prax import logger
from aipass.cli.apps.modules import console

from aipass.backup.apps.handlers.json import json_handler


MODULE_NAME = "drive_stats"
PRIMARY_COMMAND = "drive-stats"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 4 -- tracker statistics")
    console.print("  Handlers: drive/tracker")


def print_help():
    """Display help for this module."""
    print_introspection()
    console.print()
    console.print("Usage: drive-stats <project_root>")


def run_drive_stats(project_root: str) -> bool:
    """Show tracker statistics for a project.

    Args:
        project_root: Absolute path to the project.

    Returns:
        True if stats were displayed, False on error.
    """
    from aipass.backup.apps.handlers.drive.tracker import (
        get_stats,
        load_tracker,
    )

    try:
        tracker = load_tracker(project_root)
        stats = get_stats(tracker)

        console.print(f"[bold cyan]Drive Tracker Stats[/bold cyan] -- {project_root}")
        console.print(f"  Total tracked files: {stats['total']}")

        if stats.get("sample"):
            console.print("  Sample entries:")
            for key, entry in stats["sample"].items():
                drive_id = entry.get("drive_id", "?")
                console.print(f"    {key}: {drive_id}")

        json_handler.log_operation(
            "drive_stats_displayed",
            {"project_root": project_root, "total": stats["total"]},
        )
        logger.info(f"[backup] Drive stats: {stats['total']} tracked files")
        return True
    except Exception as exc:
        logger.warning(f"Failed to load tracker for {project_root}: {exc}")
        console.print(f"[red]Error loading tracker: {exc}[/red]")
        return False


def handle_command(command: str, args: list) -> bool:
    """Handle the drive-stats command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_help()
        return True

    project_root = args[0]
    run_drive_stats(project_root)
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_introspection()
        sys.exit(0)
    handle_command(PRIMARY_COMMAND, sys.argv[1:])
