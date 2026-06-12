# =================== AIPass ====================
# Name: all.py
# Description: All module — full cycle: snapshot + versioned (shared scan)
# Version: 3.0.0
# Created: 2026-04-17
# Modified: 2026-06-12
# =============================================

"""All Module — runs snapshot then versioned backup with shared scan."""

import sys

from aipass.prax import logger
from aipass.cli.apps.modules import console

from aipass.backup.apps.handlers.ignore.patterns import load_patterns
from aipass.backup.apps.handlers.ignore.whitelist import load_whitelist
from aipass.backup.apps.handlers.json import json_handler
from aipass.backup.apps.handlers.project.config import load_project_config
from aipass.backup.apps.handlers.scan.filter import filter_paths
from aipass.backup.apps.handlers.scan.walk import walk_project
from aipass.backup.apps.modules.snapshot import run_snapshot
from aipass.backup.apps.modules.versioned import run_versioned

MODULE_NAME = "all"
PRIMARY_COMMAND = "all"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 3 — shared scan")
    console.print("  Orchestration: scan -> snapshot -> versioned")


def print_help():
    """Display help for this module."""
    print_introspection()


def handle_command(command: str, args: list) -> bool:
    """Handle the all command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_introspection()
        return True

    project_root = args[0]
    logger.info(f"[backup] Running full backup cycle for {project_root}")

    # ONE scan shared between both modes (Patrick's Law #1)
    config = load_project_config(project_root)
    patterns = load_patterns(project_root)
    whitelist_entries = load_whitelist(project_root)
    max_size = config.get("max_file_size_mb", 100)
    all_files = list(walk_project(project_root))
    filtered = filter_paths(all_files, patterns, whitelist_entries, max_size)

    snap_result = run_snapshot(project_root)
    console.print()

    ver_result = run_versioned(project_root, pre_scanned=filtered)

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
