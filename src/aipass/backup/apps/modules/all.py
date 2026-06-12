# =================== AIPass ====================
# Name: all.py
# Description: All module — full cycle: snapshot + versioned
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-04-23
# =============================================

"""All Module — runs snapshot then versioned backup in sequence."""

import sys

from aipass.prax import logger
from aipass.cli.apps.modules import console

from apps.handlers.json import json_handler
from apps.handlers.report.formatter import format_result
from apps.modules.snapshot import run_snapshot
from apps.modules.versioned import run_versioned

MODULE_NAME = "all"
PRIMARY_COMMAND = "all"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 3 — implemented")
    console.print("  Orchestration: snapshot -> versioned")


def handle_command(command: str, args: list) -> bool:
    """Handle the all command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    project_root = args[0]
    logger.info(f"[backup] Running full backup cycle for {project_root}")

    snap_result = run_snapshot(project_root)
    console.print(format_result(snap_result))
    console.print("")

    ver_result = run_versioned(project_root)
    console.print(format_result(ver_result))

    json_handler.log_operation(
        "all_complete",
        {
            "project_root": project_root,
            "snapshot_files": snap_result.files_copied,
            "versioned_files": ver_result.files_copied,
        },
    )
    logger.info(
        f"[backup] Full backup complete: snapshot={snap_result.files_copied}, versioned={ver_result.files_copied}"
    )
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_introspection()
        sys.exit(0)
    handle_command(PRIMARY_COMMAND, sys.argv[1:])
